# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from copy import deepcopy

from deepmerge import always_merger


def deep_merge(*dicts: dict) -> dict:
    """Merges two dictionaries

    Returns:
        dict: Merged dictionary
    """
    merged = {}
    for d in dicts:
        tmp = deepcopy(d)
        merged = always_merger.merge(merged, tmp)
    return merged
