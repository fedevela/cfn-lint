"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import regex as re

from cfnlint._typing import RuleMatches
from cfnlint.rules import CloudFormationLintRule, RuleMatch
from cfnlint.template import Template


class HardCodedArnProperties(CloudFormationLintRule):
    """
    Checks Resources if ARNs use correctly placed Pseudo Parameters
    instead of hardcoded Partition, Region, and Account Number
    """

    id = "I3042"
    shortdesc = "ARNs should use correctly placed Pseudo Parameters"
    description = (
        "Checks Resources if ARNs use correctly placed Pseudo Parameters instead of"
        " hardcoded Partition, Region, and Account Number"
    )
    source_url = ""
    tags = ["resources"]

    # ARCHITECTURE [I3042-OAI-001, I3042-OAI-002, I3042-OAI-008]
    # Ownership remains inside I3042: ARN extraction supplies locally parsed
    # partition/service/region/account/resource context to match(), and match()
    # owns the narrow canonical-OAI account exception.  The exception must not
    # become a shared account allowlist or a dependency of partition/region
    # validation.  This extractor-to-policy seam uses only template content and
    # rule configuration; no AWS session, network, credential, or OS adapter
    # belongs on either side of the boundary.
    # using \r\n inside ${ } because there can be spaces in the sub parameter naming
    # using \s for matching outside of Sub parameters as no space will work
    regex = re.compile(
        r"arn:(\$\{[^:\r\n]*::[^:\r\n]*}|[^:\s]*):[^:\s]+:(\$\{[^:\r\n]*::[^:\r\n]*}|[^:\s]*):(\$\{[^:\r\n]*::[^:\r\n]*}|[^:\s]*)"
    )
    # ARCHITECTURE [I3042-OAI-005, I3042-OAI-006]
    # This full-ARN recognizer is the sole producer of canonical-OAI context.
    # _match_values() transmits its boolean result beside the parsed segments;
    # match() consumes that result at the account-policy boundary.  Keep the
    # contract directional and narrow: the literal account value "cloudfront"
    # cannot create the context itself, and no generic nonnumeric-account
    # predicate belongs between extraction and account validation.
    canonical_oai_regex = re.compile(
        r"arn:\$\{AWS::Partition}:iam::cloudfront:"
        r"user/CloudFront Origin Access Identity [^\s/]+"
    )

    def __init__(self):
        """Init"""
        super().__init__()
        self.config_definition = {
            "partition": {
                "default": True,
                "type": "boolean",
            },
            "region": {
                "default": False,
                "type": "boolean",
            },
            "accountId": {
                "default": False,
                "type": "boolean",
            },
        }

        self.configure()

    def _match_values(self, cfnelem, path):
        """Recursively search for values matching the searchRegex"""
        values = []
        if isinstance(cfnelem, dict):
            for key in cfnelem:
                pathprop = path[:]
                pathprop.append(key)
                values.extend(self._match_values(cfnelem[key], pathprop))
        elif isinstance(cfnelem, list):
            for index, item in enumerate(cfnelem):
                pathprop = path[:]
                pathprop.append(index)
                values.extend(self._match_values(item, pathprop))
        else:
            # Leaf node
            if isinstance(cfnelem, str):  # and re.match(searchRegex, cfnelem):
                canonical_oai = bool(self.canonical_oai_regex.fullmatch(cfnelem))
                for variable in re.findall(self.regex, cfnelem):
                    if "Fn::Sub" in path:
                        values.append(path + [variable + (canonical_oai,)])

        return values

    def match_values(self, cfn):
        """
        Search for values in all parts of the templates that match the searchRegex
        """
        results = []
        results.extend(self._match_values(cfn.template.get("Resources", {}), []))
        # Globals are removed during a transform.  They need to be checked manually
        results.extend(self._match_values(cfn.template.get("Globals", {}), []))
        return results

    def match(self, cfn: Template) -> RuleMatches:
        matches: RuleMatches = []

        transforms = cfn.transform_pre["Transform"]
        transforms = transforms if isinstance(transforms, list) else [transforms]
        if "AWS::Serverless-2016-10-31" in cfn.transform_pre["Transform"]:
            return matches

        # Get a list of paths to every leaf node string containing at least one ${parameter}
        parameter_string_paths = self.match_values(cfn)
        # We want to search all of the paths to check if each one contains an 'Fn::Sub'
        for parameter_string_path in parameter_string_paths:
            path = ["Resources"] + parameter_string_path[:-1]
            candidate = parameter_string_path[-1]

            # PSEUDOCODE [I3042-OAI-001, I3042-OAI-002, I3042-OAI-008]
            # INPUT: the locally parsed ARN segments, source path, and I3042 config.
            # DERIVE canonical_oai as true only when all of these fields match:
            #   partition = ${AWS::Partition}; service = iam; region = empty;
            #   account = cloudfront; resource type = user; and resource value =
            #   "CloudFront Origin Access Identity <nonempty identity-id>".
            # I3042-OAI-002: when partition checking is enabled, route
            # ${AWS::Partition} through the existing accepted-partition path;
            # otherwise preserve the existing partition finding.
            # I3042-OAI-001: when accountId checking is enabled and canonical_oai
            # is true, accept the literal cloudfront account without a finding.
            # When canonical_oai is false, route cloudfront and every other account
            # through the existing account validation so arbitrary nonnumeric,
            # hardcoded, or misplaced values retain their findings.
            # Preserve region validation independently; the exception must neither
            # accept a nonempty region nor alter any existing region outcome.
            # I3042-OAI-008: compute every decision solely from template content and
            # rule configuration; perform no credential, network, or OS-dependent
            # lookup, so macOS and Ubuntu transition to the same matches output.

            # ruff: noqa: E501
            # !Sub arn:${AWS::Partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
            # is valid even with aws as the account #.  This handles empty string
            if self.config["partition"] and not re.match(
                r"^\$\{\w+}|\$\{AWS::Partition}|$", candidate[0]
            ):
                # or not re.match(r'^(\$\{\w+}|\$\{AWS::Region}|)$',candidate[1])
                # or not re.match(r'^\$\{\w+}|\$\{AWS::AccountId}|aws|$', candidate[2]):
                message = (
                    "ARN in Resource {0} contains hardcoded Partition in ARN or"
                    " incorrectly placed Pseudo Parameters"
                )
                matches.append(RuleMatch(path, message.format(path[1])))
            if self.config["region"] and not re.match(
                r"^(\$\{\w+}|\$\{AWS::Region}|)$", candidate[1]
            ):
                # or  or not re.match(r'^\$\{\w+}|\$\{AWS::AccountId}|aws|$', candidate[2]):
                message = (
                    "ARN in Resource {0} contains hardcoded Region in ARN or"
                    " incorrectly placed Pseudo Parameters"
                )
                matches.append(RuleMatch(path, message.format(path[1])))

            # Lambda is added for authorizer's Uniform Resource Identifier (URI)
            # https://github.com/aws-cloudformation/cfn-lint/issues/3716
            # ARCHITECTURE [I3042-OAI-003, I3042-OAI-004, I3042-OAI-005,
            # I3042-OAI-006]
            # Account-segment acceptance is owned by this I3042 match boundary:
            # _match_values() supplies candidate[2] as the account segment and
            # candidate[3] as narrowly scoped canonical-OAI context.  Both rejected
            # literals and misplaced pseudo parameters leave through the existing
            # RuleMatch reporting seam.  Keep this policy local to I3042 so neither
            # ARN extraction nor the canonical-OAI exception becomes a general
            # account allowlist, and keep partition/region validation independent.
            # The only dependency from account policy back to OAI recognition is
            # candidate[3]; candidate[2] remains subject to the existing accepted-
            # account contract whenever that canonical context is false.
            # PSEUDOCODE [I3042-OAI-003, I3042-OAI-004, I3042-OAI-005,
            # I3042-OAI-006]
            # INPUT: accountId configuration, the parsed account segment in
            # candidate[2], the canonical-OAI decision in candidate[3], source
            # path, and the accumulated matches.
            # IF accountId checking is disabled, do not perform an account
            # decision and continue with the next extracted ARN candidate.
            # OTHERWISE classify candidate[2] with the existing accepted-account
            # forms, including a correctly placed ${AWS::AccountId}.
            # IF the account form is accepted OR the candidate is canonical OAI,
            # preserve the accumulated matches and continue to the next candidate.
            # ELSE route both preservation obligations to the same account-ID
            # finding transition:
            #   I3042-OAI-003: a literal hardcoded account ID is not an accepted
            #   account form, so append the account-ID finding at the source path.
            #   I3042-OAI-004: a pseudo parameter that is not valid in the account
            #   segment is incorrectly placed, so append that same finding.
            #   I3042-OAI-005: when the account is the literal cloudfront, consult
            #   only the canonical-OAI decision; if false, do not exempt it and
            #   append the account-ID finding through this rejected branch.
            #   I3042-OAI-006: when the account is any other nonnumeric literal,
            #   accept it only if it is an explicitly supported account form;
            #   otherwise append the account-ID finding through this same branch.
            # OUTPUT: exactly one account-ID finding for this rejected candidate;
            # retain earlier findings and continue evaluating remaining candidates.
            # FAILURE PATH: an unrecognized account form fails closed through the
            # rejected-candidate branch; do not broaden the accepted forms here.
            valid_account = bool(
                re.match(
                    r"^\$\{\w+}|\$\{AWS::AccountId}|aws|lambda|$", candidate[2]
                )
            )
            if self.config["accountId"] and not (valid_account or candidate[3]):
                message = (
                    "ARN in Resource {0} contains hardcoded AccountId in ARN or"
                    " incorrectly placed Pseudo Parameters"
                )
                matches.append(RuleMatch(path, message.format(path[1])))

        return matches
