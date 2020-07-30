# Copyright 2020 Least Authority TFA GmbH
# See COPYING for details.

"""
Implements the magic-folder list command.
"""
import os
import json

from twisted.internet import reactor
from twisted.internet.defer import (
    inlineCallbacks,
    returnValue,
)
from twisted.web.client import (
    Agent,
    readBody,
)

from hyperlink import  DecodedURL
from treq.client import HTTPClient
from allmydata.client import read_config

def get_magic_folder_url(node_directory):
    """
    :param str node_directory: A Tahoe client directory

    :returns: base URL for the given Magic Folder instance.
    """
    magic_folder_url_file = os.path.join(node_directory, u"magic-folder.url")
    with open(magic_folder_url_file, "r") as f:
        magic_folder_url = f.read().strip()
    return magic_folder_url


@inlineCallbacks
def magic_folder_list(options):
    """
    List all folders

    :param options: TODO

    :return: TODO JSON response from `/v1/magic-folder`.
    """

    # TODO: use api_token() maybe
    config = read_config(options.parent.node_directory, u"node_port")
    auth_token = config.get_private_config("api_auth_token")

    magic_folder_url = get_magic_folder_url(options.parent.node_directory)

    # print("magic_folder_url:{} type(magic_folder_url):{}".format(magic_folder_url, type(magic_folder_url)))

    url = DecodedURL.from_text(
        unicode(magic_folder_url, 'utf-8')
    ).child(u'v1').child(u'magic-folder')

    print("url:{}".format(url))

    # encoded_url = url_to_bytes(url)

    headers = {
        b"Authorization": u"Bearer {}".format(auth_token).encode("ascii"),
    }

    treq = HTTPClient(Agent(reactor))

    response = yield treq.get(
        url.to_uri().to_text().encode('ascii'),
        headers=headers,
    )

    result = yield readBody(response)

    returnValue(result)
