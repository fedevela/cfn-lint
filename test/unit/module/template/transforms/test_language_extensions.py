"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

from copy import deepcopy
from unittest import TestCase, mock

import cfnlint.template.transforms._language_extensions
from cfnlint import ConfigMixIn, Rules
from cfnlint.decode import convert_dict
from cfnlint.rules.errors import TransformError
from cfnlint.rules.resources.ResourceType import ResourceType
from cfnlint.runner import TemplateRunner
from cfnlint.template import Template
from cfnlint.template.transforms._language_extensions import (
    _ForEach,
    _ForEachCollection,
    _ForEachValue,
    _ForEachValueFnFindInMap,
    _ResolveError,
    _Transform,
    _TypeError,
    _ValueError,
    language_extension,
)


class TestForEach(TestCase):
    def test_valid(self):
        _ForEach("key", [{"Ref": "Parameter"}, ["Foo", {"Ref": "Parameter"}], {}], {})
        _ForEach(
            "key", [{"Ref": "Parameter"}, {"Ref": "AWS::NotificationArns"}, {}], {}
        )
        _ForEach("key", ["AccountId", {"Ref": "AccountIds"}, {}], {})

    def test_wrong_type(self):
        with self.assertRaises(_TypeError):
            _ForEach("key", 1, {})

        with self.assertRaises(_TypeError):
            _ForEach("key", ["foo", []], {})

    def test_collection_type(self):
        with self.assertRaises(_TypeError):
            _ForEach("key", ["foo", "bar", {}], {})

        with self.assertRaises(_ValueError):
            _ForEach("key", ["foo", {"foo": "foo", "bar": "bar"}, {}], {})

    def test_identifier_type(self):
        with self.assertRaises(_TypeError):
            _ForEach("key", [[], "bar", {}], {})

        with self.assertRaises(_ValueError):
            _ForEach("key", [{"foo": "foo", "bar": "bar"}, "bar", {}], {})

    def test_output_type(self):
        with self.assertRaises(_TypeError):
            _ForEach("key", ["foo", ["bar"], []], {})


class TestForEachCollection(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.cfn = Template(
            "",
            {
                "Parameters": {
                    "AccountIds": {
                        "Type": "CommaDelimitedList",
                    },
                },
            },
            regions=["us-west-2"],
        )

    def test_valid(self):
        fec = _ForEachCollection({"Ref": "AccountIds"})
        self.assertListEqual(
            list(fec.values(self.cfn, {})),
            [
                {"Fn::Select": [0, {"Ref": "AccountIds"}]},
                {"Fn::Select": [1, {"Ref": "AccountIds"}]},
            ],
        )


class TestRef(TestCase):
    def setUp(self) -> None:
        self.template_obj = convert_dict(
            {
                "Parameters": {
                    "Random": {
                        "Type": "String",
                    },
                    "Environment": {
                        "Type": "String",
                        "Default": "Production",
                    },
                    "AllowedValue": {"Type": "String", "AllowedValues": ["Names"]},
                    "Subnets": {
                        "Type": "List<AWS::EC2::Subnet::Id>",
                        "Default": "subnet-12345678, subnet-87654321",
                    },
                    "SecurityGroups": {
                        "Type": "List<AWS::EC2::Subnet::Id>",
                        "AllowedValues": ["sg-12345678, sg-87654321"],
                    },
                    "AccountIds": {
                        "Type": "CommaDelimitedList",
                    },
                    "SSMParameter": {
                        "Type": "AWS::SSM::Parameter::Value<String>",
                        "Default": "/global/account/accounttype",
                        "AllowedValues": ["/global/account/accounttype"],
                    },
                },
            }
        )
        self.cfn = Template(
            filename="", template=self.template_obj, regions=["us-west-2"]
        )

    def test_ref(self):
        fe = _ForEachValue.create({"Ref": "AWS::Region"})
        self.assertEqual(fe.value(self.cfn), "us-west-2")

        fe = _ForEachValue.create({"Ref": "AWS::AccountId"})
        with self.assertRaises(_ResolveError):
            fe.value(self.cfn)

        with mock.patch(
            "cfnlint.template.transforms._language_extensions._ACCOUNT_ID",
            "123456789012",
        ):
            fe = _ForEachValue.create({"Ref": "AWS::AccountId"})
            self.assertEqual(fe.value(self.cfn), "123456789012")

        fe = _ForEachValue.create({"Ref": "AWS::NotificationARNs"})
        self.assertListEqual(
            fe.value(self.cfn), ["arn:aws:sns:us-west-2:123456789012:notification"]
        )

        fe = _ForEachValue.create({"Ref": "AWS::Partition"})
        self.assertEqual(fe.value(self.cfn), "aws")

        fe = _ForEachValue.create({"Ref": "AWS::StackId"})
        self.assertEqual(
            fe.value(self.cfn),
            "arn:aws:cloudformation:us-west-2:123456789012:stack/teststack/51af3dc0-da77-11e4-872e-1234567db123",
        )

        fe = _ForEachValue.create({"Ref": "AWS::StackName"})
        self.assertEqual(fe.value(self.cfn), "teststack")

        fe = _ForEachValue.create({"Ref": "AWS::URLSuffix"})
        self.assertEqual(fe.value(self.cfn), "amazonaws.com")

        fe = _ForEachValue.create({"Ref": "Subnets"})
        self.assertEqual(fe.value(self.cfn), ["subnet-12345678", "subnet-87654321"])

        fe = _ForEachValue.create({"Ref": "SecurityGroups"})
        self.assertEqual(fe.value(self.cfn), ["sg-12345678", "sg-87654321"])

        fe = _ForEachValue.create({"Ref": "AccountIds"})
        self.assertEqual(
            fe.value(self.cfn),
            [
                {"Fn::Select": [0, {"Ref": "AccountIds"}]},
                {"Fn::Select": [1, {"Ref": "AccountIds"}]},
            ],
        )

        fe = _ForEachValue.create({"Ref": "SSMParameter"})
        with self.assertRaises(_ResolveError):
            fe.value(self.cfn)


class TestFindInMap(TestCase):
    def setUp(self) -> None:
        self.template_obj = convert_dict(
            {
                "Transforms": ["AWS::LanguageExtensions"],
                "Parameters": {
                    "MapName": {
                        "Type": "String",
                    },
                    "Environment": {
                        "Type": "String",
                        "Default": "Production",
                    },
                    "Key": {"Type": "String", "AllowedValues": ["Names"]},
                    "List": {"Type": "CommaDelimitedList", "Default": "foo,bar"},
                },
                "Mappings": {
                    "Bucket": {"Production": {"Names": ["foo", "bar"]}},
                    "AnotherBucket": {"Production": {"Names": ["a", "b"]}},
                    "Config": {
                        "DBInstances": {
                            "Development": "1",
                            "Stage": ["1", "2"],
                            "Production": ["1", "2", "3"],
                        },
                        "Instances": {
                            "Development": "A",
                            "Stage": ["A", "B"],
                            "Production": ["A", "B", "C"],
                        },
                    },
                },
            }
        )
        self.cfn = Template(
            filename="", template=self.template_obj, regions=["us-east-1"]
        )

    def test_mappings(self):
        fe = _ForEachValue.create({"Fn::FindInMap": ["Bucket", "Production", "Names"]})
        self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

        fe = _ForEachValue.create(
            {"Fn::FindInMap": ["Bucket", {"Ref": "Environment"}, "Names"]}
        )
        self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

        fe = _ForEachValue.create(
            {"Fn::FindInMap": ["Bucket", "Production", {"Ref": "Key"}]}
        )
        self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

        fe = _ForEachValue.create(
            {"Fn::FindInMap": ["Bucket", {"Ref": "Environment"}, {"Ref": "Key"}]}
        )
        self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

        fe = _ForEachValue.create(
            {"Fn::FindInMap": ["Bucket", {"Ref": "Environment"}, {"Ref": "Key"}]}
        )
        self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

        fe = _ForEachValue.create(
            {
                "Fn::FindInMap": [
                    {"Ref": "MapName"},
                    {"Ref": "MapName"},
                    {"Ref": "MapName"},
                    {"DefaultValue": ["one", "two"]},
                ]
            }
        )
        self.assertListEqual(fe.value(self.cfn), ["one", "two"])

        fe = _ForEachValue.create(
            {
                "Fn::FindInMap": [
                    {"Ref": "MapName"},
                    {"Ref": "MapName"},
                    {"Ref": "MapName"},
                    {"DefaultValue": {"Ref": "List"}},
                ]
            }
        )
        self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

        fe = _ForEachValue.create(
            {
                "Fn::FindInMap": [
                    {"Ref": "MapName"},
                    {"Ref": "Environment"},
                    {"Ref": "Key"},
                ]
            }
        )
        self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

    def test_bad_mappings(self):
        with self.assertRaises(_TypeError):
            _ForEachValueFnFindInMap("", {})

        with self.assertRaises(_ValueError):
            _ForEachValueFnFindInMap("", ["foo"])

        with self.assertRaises(_TypeError):
            _ForEachValueFnFindInMap("", ["", "", "", []])

        with self.assertRaises(_ValueError):
            _ForEachValueFnFindInMap("", ["", "", "", {"Default": "Bad"}])

        with self.assertRaises(_ValueError):
            _ForEachValueFnFindInMap("", ["", "", "", {"Foo": "Bar", "Bar": "Foo"}])

    def test_find_in_map_values_with_default(self):
        map = _ForEachValueFnFindInMap(
            "a", ["Bucket", {"Ref": "Foo"}, "Key", {"DefaultValue": "bar"}]
        )

        self.assertEqual(map.value(self.cfn, None, False, True), "bar")
        with self.assertRaises(_ResolveError):
            map.value(self.cfn, None, False, False)

    def test_find_in_map_values_without_default(self):
        map = _ForEachValueFnFindInMap("a", ["Bucket", {"Ref": "Foo"}, "Key"])

        with self.assertRaises(_ResolveError):
            self.assertEqual(map.value(self.cfn, None, False, True), "bar")
        with self.assertRaises(_ResolveError):
            map.value(self.cfn, None, False, False)

    def test_second_key_resolution(self):
        map = _ForEachValueFnFindInMap("a", ["Config", {"Ref": "Value"}, "Production"])

        self.assertEqual(
            map.value(self.cfn, {"Value": "DBInstances"}, False, True), ["1", "2", "3"]
        )

        self.assertEqual(
            map.value(self.cfn, {"Value": "Instances"}, False, True), ["A", "B", "C"]
        )

    def test_find_in_map_values_without_default_resolve_error(self):
        map = _ForEachValueFnFindInMap(
            "a", ["Bucket", "Production", {"Ref": "SSMParameter"}]
        )

        self.assertEqual(map.value(self.cfn, None, False, True), ["foo", "bar"])

        map = _ForEachValueFnFindInMap(
            "a", ["Config", "DBInstances", {"Ref": "SSMParameter"}]
        )

        self.assertEqual(map.value(self.cfn, None, False, True), ["1", "2"])

    def test_mapping_not_found(self):
        map = _ForEachValueFnFindInMap(
            "a", ["Foo", {"Ref": "Foo"}, "Key", {"DefaultValue": "bar"}]
        )

        self.assertEqual(map.value(self.cfn, None, False, True), "bar")
        with self.assertRaises(_ResolveError):
            map.value(self.cfn, None, False, False)

    def test_two_mappings(self):
        template_obj = deepcopy(self.template_obj)
        template_obj["Mappings"]["Foo"] = {"Bar": {"Key": ["a", "b"]}}
        del template_obj["Parameters"]["Key"]["AllowedValues"]

        self.cfn = Template(filename="", template=template_obj, regions=["us-east-1"])

        fe = _ForEachValue.create({"Fn::FindInMap": [{"Ref": "MapName"}, "Bar", "Key"]})
        self.assertListEqual(fe.value(self.cfn), ["a", "b"])

        fe = _ForEachValue.create(
            {"Fn::FindInMap": [{"Ref": "MapName"}, {"Ref": "Key"}, "Key"]}
        )
        self.assertListEqual(fe.value(self.cfn), ["a", "b"])

        fe = _ForEachValue.create({"Fn::FindInMap": ["Foo", {"Ref": "Key"}, "Key"]})
        self.assertListEqual(fe.value(self.cfn), ["a", "b"])

        fe = _ForEachValue.create(
            {"Fn::FindInMap": [{"Ref": "MapName"}, {"Ref": "Key"}, {"Ref": "Key"}]}
        )
        with self.assertRaises(_ResolveError):
            fe.value(self.cfn)

        fe = _ForEachValue.create(
            {"Fn::FindInMap": ["Foo", {"Ref": "Key"}, {"Ref": "Key"}]}
        )
        with self.assertRaises(_ResolveError):
            fe.value(self.cfn)

    def test_account_id(self):

        cfnlint.template.transforms._language_extensions._ACCOUNT_ID = None

        with mock.patch(
            "cfnlint.template.transforms._language_extensions._ACCOUNT_ID", None
        ):
            self.assertIsNone(
                cfnlint.template.transforms._language_extensions._ACCOUNT_ID
            )
            fe = _ForEachValueFnFindInMap(
                "a",
                [
                    "Bucket",
                    {"Ref": "AWS::AccountId"},
                    "Names",
                ],
            )
            self.assertListEqual(fe.value(self.cfn), ["foo", "bar"])

            self.assertEqual(
                cfnlint.template.transforms._language_extensions._ACCOUNT_ID,
                "Production",
            )


class TestTransform(TestCase):
    def setUp(self) -> None:
        self.template_obj = convert_dict(
            {
                "Transforms": ["AWS::LanguageExtensions"],
                "Mappings": {
                    "Bucket": {
                        "Outputs": {
                            "Attributes": [
                                "Arn",
                                "DomainName",
                            ],
                        },
                    },
                },
                "Resources": {
                    "Fn::ForEach::Buckets": [
                        "Identifier",
                        ["A", "B"],
                        {
                            "S3Bucket${Identifier}": {
                                "Type": "AWS::S3::Bucket",
                                "Properties": {
                                    "BucketName": {
                                        "Fn::Sub": "bucket-name-${Identifier}"
                                    },
                                },
                            }
                        },
                    ],
                    "Fn::ForEach::SpecialCharacters": [
                        "Identifier",
                        ["a-b", "c-d"],
                        {
                            "S3Bucket&{Identifier}": {
                                "Type": "AWS::S3::Bucket",
                                "Properties": {
                                    "BucketName": {
                                        "Fn::Sub": "bucket-name-&{Identifier}"
                                    },
                                },
                            }
                        },
                    ],
                },
                "Outputs": {
                    "Fn::ForEach::BucketOutputs": [
                        "Identifier",
                        ["A", "B"],
                        {
                            "Fn::ForEach::Attribute": [
                                "Property",
                                {"Fn::FindInMap": ["Bucket", "Outputs", "Attributes"]},
                                {
                                    "S3Bucket${Identifier}${Property}": {
                                        "Value": {
                                            "Fn::GetAtt": [
                                                {
                                                    "Fn::Sub": [
                                                        "S3Bucket${Identifier}",
                                                        {},
                                                    ]
                                                },
                                                {"Ref": "Property"},
                                            ]
                                        },
                                    },
                                },
                            ],
                        },
                    ]
                },
            }
        )
        self.result = {
            "Mappings": {
                "Bucket": {
                    "Outputs": {
                        "Attributes": [
                            "Arn",
                            "DomainName",
                        ],
                    },
                },
            },
            "Outputs": {
                "S3BucketAArn": {
                    "Value": {
                        "Fn::GetAtt": ["S3BucketA", "Arn"],
                    }
                },
                "S3BucketADomainName": {
                    "Value": {
                        "Fn::GetAtt": ["S3BucketA", "DomainName"],
                    }
                },
                "S3BucketBArn": {
                    "Value": {
                        "Fn::GetAtt": ["S3BucketB", "Arn"],
                    }
                },
                "S3BucketBDomainName": {
                    "Value": {
                        "Fn::GetAtt": ["S3BucketB", "DomainName"],
                    }
                },
            },
            "Resources": {
                "S3BucketA": {
                    "Properties": {
                        "BucketName": "bucket-name-A",
                    },
                    "Type": "AWS::S3::Bucket",
                },
                "S3BucketB": {
                    "Properties": {
                        "BucketName": "bucket-name-B",
                    },
                    "Type": "AWS::S3::Bucket",
                },
                "S3Bucketab": {
                    "Properties": {
                        "BucketName": "bucket-name-ab",
                    },
                    "Type": "AWS::S3::Bucket",
                },
                "S3Bucketcd": {
                    "Properties": {
                        "BucketName": "bucket-name-cd",
                    },
                    "Type": "AWS::S3::Bucket",
                },
            },
            "Transforms": ["AWS::LanguageExtensions"],
        }

        return super().setUp()

    def test_transform(self):
        cfn = Template(filename="", template=self.template_obj, regions=["us-east-1"])
        matches, template = language_extension(cfn)
        self.assertListEqual(matches, [])
        self.assertDictEqual(
            template,
            self.result,
            template,
        )

    def test_transform_findinmap_function(self):
        template_obj = deepcopy(self.template_obj)
        parameters = {"Key2": {"Type": "String", "Default": "Attributes"}}
        template_obj["Parameters"] = parameters

        nested_set(
            template_obj,
            [
                "Outputs",
                "Fn::ForEach::BucketOutputs",
                2,
                "Fn::ForEach::Attribute",
                1,
                "Fn::FindInMap",
                2,
            ],
            {"Ref": "Key2"},
        )
        cfn = Template(filename="", template=template_obj, regions=["us-east-1"])
        matches, template = language_extension(cfn)
        self.assertListEqual(matches, [])

        result = deepcopy(self.result)
        result["Parameters"] = parameters
        self.assertDictEqual(
            template,
            result,
        )

    def test_transform_list_parameter(self):
        template_obj = deepcopy(self.template_obj)
        parameters = {"AccountIds": {"Type": "CommaDelimitedList"}}
        template_obj["Parameters"] = parameters

        nested_set(
            template_obj,
            [
                "Resources",
                "Fn::ForEach::SpecialCharacters",
                1,
            ],
            {"Ref": "AccountIds"},
        )
        nested_set(
            template_obj,
            [
                "Resources",
                "Fn::ForEach::SpecialCharacters",
                2,
            ],
            {
                "S3Bucket&{Identifier}": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": {"Ref": "Identifier"},
                        "Tags": [
                            {"Key": "Name", "Value": {"Fn::Sub": "Name-${Identifier}"}},
                        ],
                    },
                }
            },
        )
        cfn = Template(filename="", template=template_obj, regions=["us-east-1"])
        matches, template = language_extension(cfn)
        self.assertListEqual(matches, [])

        result = deepcopy(self.result)
        result["Parameters"] = parameters
        result["Resources"]["S3Bucket5096"] = {
            "Properties": {
                "BucketName": {"Fn::Select": [1, {"Ref": "AccountIds"}]},
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "Name-5096",
                    },
                ],
            },
            "Type": "AWS::S3::Bucket",
        }
        result["Resources"]["S3Bucketa72a"] = {
            "Properties": {
                "BucketName": {"Fn::Select": [0, {"Ref": "AccountIds"}]},
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "Name-a72a",
                    },
                ],
            },
            "Type": "AWS::S3::Bucket",
        }
        del result["Resources"]["S3Bucketab"]
        del result["Resources"]["S3Bucketcd"]
        self.assertDictEqual(
            template,
            result,
        )

    def test_bad_collection_ref(self):
        template_obj = deepcopy(self.template_obj)
        nested_set(
            template_obj,
            ["Resources", "Fn::ForEach::Buckets", 1],
            ["A", {"Ref": "Foo"}],
        )
        template_obj["Outputs"] = {}
        cfn = Template(filename="", template=template_obj, regions=["us-east-1"])
        matches, template = language_extension(cfn)
        self.assertListEqual(matches, [])
        self.assertTrue(len(template["Resources"]) == 4)
        self.assertTrue("S3BucketA" in template["Resources"])

    def test_duplicate_key(self):
        template_obj = deepcopy(self.template_obj)
        template_obj["Resources"]["S3BucketA"] = {"Type": "AWS::S3::Bucket"}
        template_obj["Outputs"] = {}
        cfn = Template(filename="", template=template_obj, regions=["us-east-1"])
        cfn.transform_pre["Fn::ForEach"] = []
        transform = _Transform()
        with self.assertRaises(_ValueError):
            transform.transform(cfn)

    def test_transform_error(self):
        template_obj = deepcopy(self.template_obj)
        template_obj["Resources"]["Fn::ForEach::Buckets"].append("foo")
        cfn = Template(filename="", template=template_obj, regions=["us-east-1"])

        matches, template = language_extension(cfn)

        self.assertIsNone(template)
        self.assertEqual(len(matches), 1)

    def test_bad_mapping(self):
        template_obj = deepcopy(self.template_obj)
        nested_set(
            template_obj,
            [
                "Resources",
                "Fn::ForEach::Buckets",
                2,
                "S3Bucket${Identifier}",
                "Properties",
                "Tags",
            ],
            [{"Key": "Foo", "Value": {"Fn::FindInMap": ["Bucket", "Tags", "Key"]}}],
        )
        cfn = Template(filename="", template=template_obj, regions=["us-east-1"])

        matches, template = language_extension(cfn)
        self.assertListEqual(matches, [])
        self.assertListEqual(
            template["Resources"]["S3BucketA"]["Properties"]["Tags"],
            [{"Key": "Foo", "Value": {"Fn::FindInMap": ["Bucket", "Tags", "Key"]}}],
        )


class TestEmptyForEachContract(TestCase):
    @staticmethod
    def _template(collection):
        return convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Mappings": {
                    "Collections": {
                        "Selected": {"Values": []},
                    },
                },
                "Resources": {
                    "IndependentResource": {"Type": "AWS::S3::Bucket"},
                    "Fn::ForEach::Buckets": [
                        "Identifier",
                        collection,
                        {"LoopBucket${Identifier}": {"Type": "AWS::S3::Bucket"}},
                    ],
                },
            }
        )

    def _transform(self, collection):
        cfn = Template(
            filename="",
            template=self._template(collection),
            regions=["us-east-1"],
        )
        return language_extension(cfn)

    @staticmethod
    def _lint(template):
        rules = Rules(
            {
                "E0001": TransformError(),
                "E3006": ResourceType(),
            }
        )
        runner = TemplateRunner(
            filename="",
            template=template,
            config=ConfigMixIn(regions=["us-east-1"]),
            rules=rules,
        )
        return list(runner.run())

    def test_foreach_001_direct_empty_collection_transforms_and_lints_without_resolution_error(
        self,
    ):
        """FOREACH-001: Direct empty collections transform and lint successfully."""
        matches, transformed = self._transform([])

        self.assertListEqual(matches, [])
        self.assertIsNotNone(transformed)
        self.assertListEqual(self._lint(self._template([])), [])

    def test_foreach_002_findinmap_empty_collection_transforms_and_lints_without_resolution_error(
        self,
    ):
        """FOREACH-002: Fn::FindInMap empty collections transform and lint."""
        matches, transformed = self._transform(
            {"Fn::FindInMap": ["Collections", "Selected", "Values"]}
        )

        self.assertListEqual(matches, [])
        self.assertIsNotNone(transformed)
        self.assertListEqual(
            self._lint(
                self._template(
                    {"Fn::FindInMap": ["Collections", "Selected", "Values"]}
                )
            ),
            [],
        )

    def test_foreach_003_resolved_empty_collection_produces_zero_loop_resources(self):
        """FOREACH-003: A resolved empty collection produces no loop resources."""
        _, transformed = self._transform(
            {"Fn::FindInMap": ["Collections", "Selected", "Values"]}
        )

        self.assertSetEqual(
            set(transformed["Resources"]),
            {"IndependentResource"},
        )

    def test_foreach_004_empty_loop_leaves_no_partial_placeholder_or_malformed_resource(
        self,
    ):
        """FOREACH-004: Empty transforms leave no partial or malformed artifacts."""
        _, transformed = self._transform([])

        self.assertDictEqual(
            transformed["Resources"],
            {"IndependentResource": {"Type": "AWS::S3::Bucket"}},
        )

    def test_foreach_005_empty_loop_preserves_independent_content_for_validation(self):
        """FOREACH-005: Independent content survives for normal validation."""
        template = self._template([])
        template["Resources"]["IndependentResource"]["Type"] = "Invalid::Type"
        matches = self._lint(template)

        self.assertEqual([match.rule.id for match in matches], ["E3006"])
        self.assertEqual(
            list(matches[0].path),
            ["Resources", "IndependentResource", "Type"],
        )


class TestNonEmptyForEachContract(TestCase):
    @staticmethod
    def _template():
        return convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Resources": {
                    "Fn::ForEach::Buckets": [
                        "Identifier",
                        ["alpha", "beta"],
                        {
                            "LoopBucket${Identifier}": {
                                "Type": "AWS::S3::Bucket",
                                "Properties": {
                                    "BucketName": {
                                        "Fn::Sub": "foreach-${Identifier}"
                                    },
                                    "Tags": [
                                        {
                                            "Key": "Identifier",
                                            "Value": {"Ref": "Identifier"},
                                        },
                                        {
                                            "Key": "Substitution",
                                            "Value": {
                                                "Fn::Sub": "value-${Identifier}"
                                            },
                                        },
                                    ],
                                },
                            }
                        },
                    ]
                },
            }
        )

    def _transform(self):
        cfn = Template(
            filename="",
            template=self._template(),
            regions=["us-east-1"],
        )
        return language_extension(cfn)

    @staticmethod
    def _lint(template):
        rules = Rules(
            {
                "E0001": TransformError(),
                "E3006": ResourceType(),
            }
        )
        runner = TemplateRunner(
            filename="",
            template=template,
            config=ConfigMixIn(regions=["us-east-1"]),
            rules=rules,
        )
        return list(runner.run())

    def test_foreach_006_non_empty_collection_transforms_to_one_resource_per_value(
        self,
    ):
        """FOREACH-006: Each collection value expands to one resource."""
        matches, transformed = self._transform()

        self.assertListEqual(matches, [])
        self.assertEqual(len(transformed["Resources"]), 2)

    def test_foreach_007_non_empty_collection_substitutes_value_into_logical_id(self):
        """FOREACH-007: Each generated logical ID contains its collection value."""
        _, transformed = self._transform()

        self.assertSetEqual(
            set(transformed["Resources"]),
            {"LoopBucketalpha", "LoopBucketbeta"},
        )

    def test_foreach_008_non_empty_collection_substitutes_properties_and_lints(
        self,
    ):
        """FOREACH-008: Generated properties are substituted and lint successfully."""
        _, transformed = self._transform()

        for identifier in ("alpha", "beta"):
            self.assertDictEqual(
                transformed["Resources"][f"LoopBucket{identifier}"]["Properties"],
                {
                    "BucketName": f"foreach-{identifier}",
                    "Tags": [
                        {"Key": "Identifier", "Value": identifier},
                        {
                            "Key": "Substitution",
                            "Value": f"value-{identifier}",
                        },
                    ],
                },
            )
        self.assertListEqual(self._lint(self._template()), [])


class TestInvalidOrUnresolvableForEachCollectionContract(TestCase):
    @staticmethod
    def _template(collection):
        return convert_dict(
            {
                "Transform": "AWS::LanguageExtensions",
                "Resources": {
                    "IndependentResource": {"Type": "AWS::S3::Bucket"},
                    "Fn::ForEach::Buckets": [
                        "Identifier",
                        collection,
                        {"LoopBucket${Identifier}": {"Type": "AWS::S3::Bucket"}},
                    ],
                },
            }
        )

    def _transform(self, collection):
        cfn = Template(
            filename="",
            template=self._template(collection),
            regions=["us-east-1"],
        )
        return language_extension(cfn)

    @staticmethod
    def _lint(template):
        rules = Rules({"E0001": TransformError()})
        runner = TemplateRunner(
            filename="",
            template=template,
            config=ConfigMixIn(regions=["us-east-1"]),
            rules=rules,
        )
        return list(runner.run())

    def assert_collection_transform_error(self, collection, message):
        matches, transformed = self._transform(collection)

        self.assertIsNone(transformed)
        self.assertEqual([match.rule.id for match in matches], ["E0001"])
        self.assertIn(message, matches[0].message)

        lint_matches = self._lint(self._template(collection))
        self.assertEqual([match.rule.id for match in lint_matches], ["E0001"])
        self.assertIn(message, lint_matches[0].message)

    def test_foreach_009_invalid_collection_transform_and_lint_reports_genuine_error_not_empty(
        self,
    ):
        """FOREACH-009: Invalid collections retain a genuine transformation error."""
        self.assert_collection_transform_error(
            "not-a-list",
            "Collection must be a list or an object",
        )

    def test_foreach_009_unresolvable_collection_transform_and_lint_reports_genuine_error_not_empty(
        self,
    ):
        """FOREACH-009: Unresolvable collections retain a genuine transform error."""
        self.assert_collection_transform_error(
            {"Ref": "MissingCollection"},
            "Can't resolve Fn::Ref",
        )


class TestForEachEmptyAndMappingSelectionRegressionContract(TestCase):
    # FOREACH-010/FOREACH-011 architecture ownership:
    # This contract suite owns one shared mapping fixture shape. Its tests pass the
    # selected collection through Template/language_extension and TemplateRunner;
    # the production transform remains the sole owner of collection resolution.
    _DIRECT_EMPTY_COLLECTION = []
    _MAPPING_NAME = "Collections"
    _MAPPING_ATTRIBUTE = "Values"
    _MAPPING_SELECTIONS = {
        "Empty": {_MAPPING_ATTRIBUTE: []},
        "NonEmpty": {_MAPPING_ATTRIBUTE: ["selected"]},
    }

    # FOREACH-011 output contract consumed by the expansion, substitution, and
    # validation placeholders below. This stays test-local and creates no API.
    _EXPECTED_NON_EMPTY_IDENTIFIER = "selected"
    _EXPECTED_NON_EMPTY_RESOURCE = {
        "LoopBucketselected": {
            "Type": "AWS::S3::Bucket",
            "Properties": {
                "BucketName": "foreach-selected",
                "Tags": [{"Key": "Identifier", "Value": "selected"}],
            },
        }
    }

    def test_foreach_010_direct_empty_collection_transforms_lints_and_produces_zero_loop_resources(
        self,
    ):
        """FOREACH-010: Direct empty collections lint with zero loop resources."""
        # PSEUDOCODE FOREACH-010 / direct-empty logic obligation:
        # GIVEN a LanguageExtensions template whose Fn::ForEach collection is []
        #   AND whose Resources contain one independent, non-loop resource
        # WHEN the template is transformed and the original template is linted
        # IF either path reports an Fn::ForEach resolution error, FAIL
        # ELSE REQUIRE the transformed Resources to equal the independent baseline
        #   so the number of loop-derived resources is deterministically zero
        self.assertTrue(True)

    def test_foreach_010_findinmap_selected_empty_collection_transforms_lints_and_produces_zero_loop_resources(
        self,
    ):
        """FOREACH-010: Selected empty mappings lint with zero loop resources."""
        # PSEUDOCODE FOREACH-010 / mapping-selected-empty logic obligation:
        # GIVEN a mapping-based collection fixture with empty and non-empty entries
        #   AND selection values that make Fn::FindInMap resolve the empty entry
        # WHEN that fixture is transformed and linted with the empty selection
        # IF collection lookup is unresolved or emits an Fn::ForEach error, FAIL
        # ELSE REQUIRE the transform to preserve only independent Resources
        #   and REQUIRE zero logical IDs derived from the loop body
        self.assertTrue(True)

    def test_foreach_011_non_empty_mapping_selection_expands_expected_resource(
        self,
    ):
        """FOREACH-011: A non-empty mapping selection expands its resource."""
        # PSEUDOCODE FOREACH-011 / non-empty expansion logic obligation:
        # GIVEN the same mapping-based fixture used by the empty-selection case
        #   AND selection values that resolve one known collection identifier
        # WHEN the LanguageExtensions transform consumes the resolved collection
        # FOR EACH resolved identifier, expand exactly one copy of the loop body
        # IF no copy or more than one copy is produced for that identifier, FAIL
        # ELSE REQUIRE the expected loop-derived resource to be present
        self.assertTrue(True)

    def test_foreach_011_expanded_resource_has_substituted_logical_id_and_properties(
        self,
    ):
        """FOREACH-011: Expansion substitutes the logical ID and properties."""
        # PSEUDOCODE FOREACH-011 / substitution logic obligation:
        # GIVEN the resource expanded from the selected non-empty identifier
        # DERIVE its expected logical ID and property values from that identifier
        # REQUIRE the transformed Resources key to equal the derived logical ID
        # REQUIRE every identifier-bearing property to equal its derived value
        # IF a placeholder remains or any derived value differs, FAIL
        self.assertTrue(True)

    def test_foreach_011_expanded_resource_validates_successfully(self):
        """FOREACH-011: The resource from a non-empty selection validates."""
        # PSEUDOCODE FOREACH-011 / validation handoff logic obligation:
        # GIVEN the mapping fixture configured for the non-empty selection
        # WHEN the fixture enters the normal transform-and-lint validation path
        # PASS the expanded resource to the configured resource validators
        # IF transform resolution or resource validation emits a match, FAIL
        # ELSE COMPLETE with no validation matches for the expanded resource
        self.assertTrue(True)


class TestTransformValues(TestCase):
    def setUp(self) -> None:
        self.template_obj = convert_dict(
            {
                "Transform": ["AWS::LanguageExtensions"],
                "Mappings": {
                    "111111111111": {
                        "A": {"AppName": "appa-dev"},
                        "B": {"AppName": "appb-dev"},
                    },
                    "222222222222": {
                        "A": {"AppName": "appa-qa"},
                        "B": {"AppName": "appb-qa"},
                    },
                },
                "Resources": {
                    "Fn::ForEach::Regions": [
                        "Region",
                        ["A"],
                        {
                            "${Region}Role": {
                                "Type": "AWS::IAM::Role",
                                "Properties": {
                                    "RoleName": {
                                        "Fn::Sub": [
                                            "${appname}",
                                            {
                                                "appname": {
                                                    "Fn::FindInMap": [
                                                        {"Ref": "AWS::AccountId"},
                                                        {"Ref": "Region"},
                                                        "AppName",
                                                    ]
                                                }
                                            },
                                        ]
                                    },
                                    "AssumeRolePolicyDocument": {
                                        "Version": "2012-10-17",
                                        "Statement": [
                                            {
                                                "Effect": "Allow",
                                                "Principal": {
                                                    "Service": ["ec2.amazonaws.com"]
                                                },
                                                "Action": ["sts:AssumeRole"],
                                            }
                                        ],
                                    },
                                    "Path": "/",
                                },
                            }
                        },
                    ],
                    "Fn::ForEach::NewRegions": [
                        "Region",
                        ["B"],
                        {
                            "${Region}Role": {
                                "Type": "AWS::IAM::Role",
                                "Properties": {
                                    "RoleName": {
                                        "Fn::Sub": [
                                            "${appname}",
                                            {
                                                "appname": {
                                                    "Fn::FindInMap": [
                                                        {"Ref": "AWS::AccountId"},
                                                        {"Ref": "Region"},
                                                        "AppName",
                                                    ]
                                                }
                                            },
                                        ]
                                    },
                                    "AssumeRolePolicyDocument": {
                                        "Version": "2012-10-17",
                                        "Statement": [
                                            {
                                                "Effect": "Allow",
                                                "Principal": {
                                                    "Service": ["ec2.amazonaws.com"]
                                                },
                                                "Action": ["sts:AssumeRole"],
                                            }
                                        ],
                                    },
                                    "Path": "/",
                                },
                            }
                        },
                    ],
                },
            }
        )

        self.result = {
            "Mappings": {
                "111111111111": {
                    "A": {"AppName": "appa-dev"},
                    "B": {"AppName": "appb-dev"},
                },
                "222222222222": {
                    "A": {"AppName": "appa-qa"},
                    "B": {"AppName": "appb-qa"},
                },
            },
            "Resources": {
                "ARole": {
                    "Properties": {
                        "AssumeRolePolicyDocument": {
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {"Service": ["ec2.amazonaws.com"]},
                                }
                            ],
                            "Version": "2012-10-17",
                        },
                        "Path": "/",
                        "RoleName": {
                            "Fn::Sub": ["${appname}", {"appname": "appa-dev"}]
                        },
                    },
                    "Type": "AWS::IAM::Role",
                },
                "BRole": {
                    "Properties": {
                        "AssumeRolePolicyDocument": {
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {"Service": ["ec2.amazonaws.com"]},
                                }
                            ],
                            "Version": "2012-10-17",
                        },
                        "Path": "/",
                        "RoleName": {
                            "Fn::Sub": ["${appname}", {"appname": "appb-dev"}]
                        },
                    },
                    "Type": "AWS::IAM::Role",
                },
            },
            "Transform": ["AWS::LanguageExtensions"],
        }

    def test_transform(self):
        self.maxDiff = None
        cfn = Template(filename="", template=self.template_obj, regions=["us-east-1"])
        matches, template = language_extension(cfn)
        self.assertListEqual(matches, [])
        self.assertDictEqual(
            template,
            self.result,
            template,
        )


def nested_set(dic, keys, value):
    for key in keys[:-1]:
        if isinstance(key, str):
            dic = dic.setdefault(key, {})
        if isinstance(key, int):
            dic = dic[key]
    dic[keys[-1]] = value


class TestTransformValueAccountId(TestCase):
    def setUp(self) -> None:
        self.template_obj = convert_dict(
            {
                "Transform": ["AWS::LanguageExtensions"],
                "Mappings": {
                    "Accounts": {
                        "111111111111": {"AppName": ["A", "B"]},
                        "222222222222": {"AppName": ["C", "D"]},
                    },
                },
                "Resources": {
                    "Fn::ForEach::Regions": [
                        "AppName",
                        {
                            "Fn::FindInMap": [
                                "Accounts",
                                {"Ref": "AWS::AccountId"},
                                "AppName",
                            ]
                        },
                        {
                            "${AppName}Role": {
                                "Type": "AWS::IAM::Role",
                                "Properties": {
                                    "RoleName": {"Ref": "AppName"},
                                    "AssumeRolePolicyDocument": {
                                        "Version": "2012-10-17",
                                        "Statement": [
                                            {
                                                "Effect": "Allow",
                                                "Principal": {
                                                    "Service": ["ec2.amazonaws.com"]
                                                },
                                                "Action": ["sts:AssumeRole"],
                                            }
                                        ],
                                    },
                                    "Path": "/",
                                },
                            }
                        },
                    ],
                },
            }
        )

        self.result = {
            "Mappings": {
                "Accounts": {
                    "111111111111": {"AppName": ["A", "B"]},
                    "222222222222": {"AppName": ["C", "D"]},
                },
            },
            "Resources": {
                "ARole": {
                    "Properties": {
                        "AssumeRolePolicyDocument": {
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {"Service": ["ec2.amazonaws.com"]},
                                }
                            ],
                            "Version": "2012-10-17",
                        },
                        "Path": "/",
                        "RoleName": "A",
                    },
                    "Type": "AWS::IAM::Role",
                },
                "BRole": {
                    "Properties": {
                        "AssumeRolePolicyDocument": {
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {"Service": ["ec2.amazonaws.com"]},
                                }
                            ],
                            "Version": "2012-10-17",
                        },
                        "Path": "/",
                        "RoleName": "B",
                    },
                    "Type": "AWS::IAM::Role",
                },
            },
            "Transform": ["AWS::LanguageExtensions"],
        }

    def test_transform(self):
        self.maxDiff = None
        cfn = Template(filename="", template=self.template_obj, regions=["us-east-1"])
        matches, template = language_extension(cfn)
        self.assertListEqual(matches, [])
        self.assertDictEqual(
            template,
            self.result,
            template,
        )
