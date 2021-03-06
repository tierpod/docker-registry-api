#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import textwrap

import requests


DEFAULT_SRV = "localhost:5000"


def parse_args():
    """Parse arguments"""

    p = argparse.ArgumentParser(description="Working with docker registry v2 api")
    p.add_argument("-s", "--server", type=str, default=DEFAULT_SRV,
                   help="Registry server [default: {0}]".format(DEFAULT_SRV))
    p.add_argument("--check", action="store_true",
                   help="Check connectivity [default action]")
    p.add_argument("--list-all", action="store_true",
                   help="List all images and tags")
    p.add_argument("--get-manifest", metavar="IMAGE:TAG", type=str,
                   help="Get image manifest")
    p.add_argument("--delete", metavar="IMAGE:TAG", type=str,
                   help="Delete image by name")
    p.add_argument("--cleanup", metavar="IMAGE", type=str)
    return p.parse_args()


def parse_imagename(image):
    """
    Parse image name

    return: (name, tag)
    """

    try:
        name, tag = image.split(":")
    except ValueError:
        name, tag = image, "latest"

    if tag == "":
        tag = "latest"

    return (name, tag)


def print_all(all_images):
    """Print all catalog information"""

    wrapper = textwrap.TextWrapper(initial_indent="  ", subsequent_indent="  ",
                                   break_on_hyphens=False)

    print("Found images total: {0}".format(len(all_images)))
    print(wrapper.fill(" ".join(all_images)))
    print("")

    for image, tags in all_images.items():
        if not tags:
            continue
        print("Tags for image: {0} (total: {1})".format(image, len(tags)))
        print(wrapper.fill(" ".join(tags)))
        print("")

    return True


class Registry(object):

    def __init__(self, base_url):
        self.base_url = base_url

    def check_connection(self):
        """
        Check connectivity to entrypoing /v2/

        Returns: bool (True if connection successful)
        """

        url = "{0}/".format(self.base_url)
        r = requests.get(url=url, verify=False)

        if r.status_code == 200 or r.status_code == 401:
            print("Connection succesful")
            return True

        return False

    def get_catalog(self):
        """Get all images catalog from repository"""

        url = "{0}/_catalog".format(self.base_url)
        catalog = requests.get(url=url, verify=False).json()["repositories"]
        return catalog

    def get_tags(self, catalog):
        """Get all tags for all images from repostiry

        Returns: dict({
            "image": ["tag", ...]
        })
        """

        result = {}
        for c in catalog:
            tags = requests.get("{0}/{1}/tags/list".format(self.base_url, c), verify=False).json()["tags"]
            result[c] = tags

        return result

    def get_all(self):
        catalog = self.get_catalog()
        return self.get_tags(catalog)

    def delete(self, name, manifest):
        """Delete image from registry by name and manifest"""

        url = "{base_url}/{name}/manifests/{manifest}".format(base_url=self.base_url,
                                                              name=name,
                                                              manifest=manifest)
        r = requests.delete(url, verify=False)
        if r.status_code == 202:
            print("Image removed successful")
            return True

        print("Error while removing image (status code: {0})".format(r.status_code))
        return True

    def get_manifest(self, name, tag):
        """
        Get manifest by image name

        Returns: str (manifest)
        """

        key = "Docker-Content-Digest"

        headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
        url = "{base_url}/{name}/manifests/{tag}".format(base_url=self.base_url,
                                                         name=name,
                                                         tag=tag)
        r = requests.get(url=url, headers=headers, verify=False)

        if key in r.headers:
            return(r.headers[key])

        print("Manifest not found")
        return None

    def cleanup(self, image, keep=10):
        """Delete old tags for image"""

        all_images = self.get_all()
        if image not in all_images:
            print("image {0} don't found".format(image))
            return

        tags = all_images[image]
        print("found {0} tags:\n  {1}".format(len(tags), ", ".join(tags)))
        for idx, tag in enumerate(tags, start=1):
            if tag == "latest":
                print("-> skip latest")
                continue
            manifest = self.get_manifest(image, tag)
            s = "[{3}/{4}] remove {0}:{1} {2}? [y/N] ".format(image, tag, manifest, idx, len(tags))
            answer = input(s)
            if answer.lower() in ["y", "yes"]:
                print("-> removing")
                self.delete(image, manifest)
            else:
                print("-> skip")


def main():
    args = parse_args()

    BASE_URL = "https://{0}/v2".format(args.server)

    # Disable InsecureRequestWarning: Unverified HTTPS request...
    requests.packages.urllib3.disable_warnings()
    registry = Registry(base_url=BASE_URL)

    if args.check:
        registry.check_connection()
    elif args.list_all:
        all_images = registry.get_all()
        print_all(all_images)
    elif args.get_manifest:
        name, tag = parse_imagename(args.get_manifest)
        manifest = registry.get_manifest(name, tag)
        print(manifest)
    elif args.delete:
        name, tag = parse_imagename(args.delete)
        manifest = registry.get_manifest(name, tag)
        if manifest:
            registry.delete(name, manifest)
        else:
            print("Image {0} not found".format(args.delete))
    elif args.cleanup:
        registry.cleanup(args.cleanup)
    else:
        # default action
        registry.check_connection()


if __name__ == "__main__":
    main()
