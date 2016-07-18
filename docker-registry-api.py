#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import requests
import textwrap

DEFAULT_SRV = 'localhost:5000'

def parse_args():
    '''
    Parse arguments
    '''
    parser = argparse.ArgumentParser(description='Get images list from docker registry')
    parser.add_argument('-s', '--server', type=str, default=DEFAULT_SRV,
                        help='Registry server [default: {0}]'.format(DEFAULT_SRV))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--list-all', action='store_true')
    parser.add_argument('--get-manifest', metavar='IMAGE', type=str)
    parser.add_argument('--delete', metavar='IMAGE', type=str)
    args = parser.parse_args()

    return args


def parse_imagename(image):
    '''
    Parse image name

    return: (name, tag)
    '''
    try:
        name, tag = image.split(':')
    except ValueError:
        name, tag = image, 'latest'

    if tag == '':
        tag = 'latest'

    return (name, tag)


def do_request(url, headers=None, verify=False, method='GET'):
    '''
    Do request

    return: reply object or exit
    '''
    print 'url: {url}'.format(url=url)
    try:
        if method == 'DELETE':
            r = requests.delete(url, headers=headers, verify=verify)
        else:
            r = requests.get(url, headers=headers, verify=verify)
        return r
    except requests.exceptions.ConnectionError as error:
        print error
        exit(1)


def check(base_url):
    '''
    Check connectivity to entrypoing /v2/

    return: True
    '''
    url = '{base_url}/'.format(base_url=base_url)
    r = do_request(url)

    if r.status_code == 200 or r.status_code == 401:
        print 'Connection succesful'
    else:
        return False

    return True


def get_manifest(base_url, image):
    '''
    Get manifest by image name

    return: {'name': name, 'tag': tag, 'manifest':manifest}
    '''
    name, tag = parse_imagename(image)
    key = 'Docker-Content-Digest'

    headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
    url = '{base_url}/{name}/manifests/{tag}'.format(base_url=base_url,
                                                     name=name,
                                                     tag=tag)
    r = do_request(url, headers=headers)
    if key in r.headers:
        print 'Manifest: {0}'.format(r.headers[key])
        return {
            'name': name,
            'tag': tag,
            'manifest': r.headers[key]
        }
    else:
        print 'Manifest not found'
        return False

    return True


def delete(base_url, manifest):
    '''
    Delete image from registry by name and manifest
    '''
    url = '{base_url}/{name}/manifests/{manifest}'.format(base_url=base_url,
                                                          name=manifest['name'],
                                                          manifest=manifest['manifest'])
    r = do_request(url, verify=False, method='DELETE')
    if r.status_code == 202:
        print "Image removed successful"
    else:
        print "Error while removing image (status code: {0})".format(r.status_code)

    return True


def list_all(base_url):
    '''
    List all images and tags in registry
    '''
    url = "{0}/_catalog".format(base_url)
    catalog = do_request(url).json()['repositories']

    wrapper = textwrap.TextWrapper(initial_indent='  ', subsequent_indent='  ',
                                   break_on_hyphens=False)

    print "Found images for registry: {0} (total: {1})".format(base_url, len(catalog))
    print wrapper.fill(' '.join(catalog))
    print ""

    for c in catalog:
        tags = requests.get("{0}/{1}/tags/list".format(base_url, c), verify=False).json()['tags']
        if tags:
            print "Tags for image: {0} (total: {1})".format(c, len(tags))
            print wrapper.fill(' '.join(tags))
        else:
            print "No tags found for image: {0}".format(c)
        print ""

    return True


if __name__ == '__main__':
    args = parse_args()

    BASE_URL = 'https://{0}/v2'.format(args.server)

    # Disable InsecureRequestWarning: Unverified HTTPS request...
    requests.packages.urllib3.disable_warnings()

    if args.check:
        check(BASE_URL)
    elif args.list_all:
        list_all(BASE_URL)
    elif args.get_manifest:
        get_manifest(BASE_URL, args.get_manifest)
    elif args.delete:
        manifest = get_manifest(BASE_URL, args.delete)
        if manifest:
            delete(BASE_URL, manifest)
        else:
            print "Image not found"
