# Copyright 2020 Least Authority TFA GmbH
# See COPYING for details.

from twisted.internet.defer import (
    inlineCallbacks,
    returnValue,
)
from hyperlink import (
    DecodedURL,
)

import attr

from .common import (
    get_node_url,
)


@attr.s
class TahoeClient(object):
    """
    An object that knows how to call a particular tahoe client's
    WebAPI. Usually this means a node-directory (to get the base URL)
    and a treq client (to make HTTP requests).

    XXX probably in a different package than this? Re-factor a couple
    things so that tahoe_mkdir() etc take a 'tahoe_client' (instead of
    a treq + node_dir)?
    """

    # node_directory = attr.ib()
    url = attr.ib()
    http_client = attr.ib()

    # XXX this is "kind-of" the start of prototyping "a Python API to Tahoe"
    # XXX for our immediate use, we need something like:

    @inlineCallbacks
    def create_immutable_directory(self, directory_data_somehow):
        pass

    @inlineCallbacks
    def create_immutable(self, file_like_reader):
        pass

    @inlineCallbacks
    def download_capability(self, cap):
        pass


@inlineCallbacks
def create_tahoe_client(node_directory, treq_client=None):
    """
    Create a new TahoeClient instance that is speaking to a particular
    Tahoe node.

    XXX is treq_client= enough of a hook to get a 'testing' treq
    client?.
    """

    # real:
    # client = create_tahoe_client(tmpdir)

    # testing:
    # root = create_fake_tahoe_root()
    # client = create_tahoe_client(tmpdir, treq_client=create_tahoe_treq_client(root))

    # from allmydata.node import read_config  ??
    base_url = get_node_url(node_directory)
    url = DecodedURL.from_text(base_url)

    if treq_client is None:
        treq_client = HTTPClient(
            agent=BrowserLikeRedirectAgent(),
        )
    client = TahoeClient(
        url=url,
        http_client=treq_client,
    )
    yield  # maybe we want to at least try getting / to see if it's alive?
    returnValue(client)