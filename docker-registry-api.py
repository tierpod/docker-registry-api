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
        if tags:
            print "Tags for image: {0} (total: {1})".format(image, len(tags))
            print wrapper.fill(" ".join(tags))
        else:
            print "No tags found for image: {0}".format(image)
        print ""

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

    def get_manifest(self, image):
        """
        Get manifest by image name

        Returns: (name, tag, manifest)
        """

        name, tag = parse_imagename(image)
        key = "Docker-Content-Digest"

        headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
        url = "{base_url}/{name}/manifests/{tag}".format(base_url=self.base_url,
                                                         name=name,
                                                         tag=tag)
        r = requests.get(url=url, headers=headers, verify=False)

        if key in r.headers:
            return(name, tag, r.headers[key])

        print("Manifest not found")
        return None


if __name__ == "__main__":
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
        _, _, manifest = registry.get_manifest(args.get_manifest)
        print(manifest)
    elif args.delete:
        manifest = registry.get_manifest(args.delete)
        if manifest:
            registry.delete(BASE_URL, manifest)
        else:
            print "Image not found"
    else:
        # default action
        registry.check_connection()
