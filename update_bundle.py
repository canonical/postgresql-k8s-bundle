#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import subprocess
import sys
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)


def fetch_revision(charm, charm_channel, ubuntu_version=None):
    """Returns revision number for charm in channel."""
    charm_info = requests.get(
        f"https://api.snapcraft.io/v2/charms/info/{charm}?fields=channel-map"
    ).json()

    [track, risk] = charm_channel.split("/")

    revisions = []
    for channel in charm_info["channel-map"]:
        if channel["channel"]["risk"] == risk and channel["channel"]["track"] == track:
            if ubuntu_version is None or ubuntu_version == channel["channel"]["base"]["channel"]:
                revisions.append(channel["revision"]["revision"])
    if revisions:
        # If the charm supports multiple Ubuntu bases, it's possible
        # that there is a different revision for each base.
        # Select the latest revision.
        return max(revisions)

    raise ValueError(
        f"Revision not found for {charm} on {charm_channel} for Ubuntu {ubuntu_version}"
    )


def update_bundle(bundle_path):
    """Updates a bundle's revision number."""
    logger.info(f"updating {bundle_path}")
    bundle_data = yaml.safe_load(Path(bundle_path).read_text())
    for app in bundle_data["applications"]:
        if series := bundle_data["applications"][app].get("series"):
            ubuntu_version = subprocess.check_output(
                ["ubuntu-distro-info", "--series", series, "--release"], encoding="utf-8"
            ).split(" ")[0]
        else:
            ubuntu_version = None
        bundle_data["applications"][app]["revision"] = fetch_revision(
            app, bundle_data["applications"][app]["channel"], ubuntu_version
        )

    logger.info("deploying bundle data")
    with open(bundle_path, "w") as bundle:
        yaml.dump(bundle_data, bundle)
        bundle.close()


if __name__ == "__main__":
    update_bundle(sys.argv[1])
