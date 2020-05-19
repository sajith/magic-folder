# Copyright 2020 Least Authority TFA GmbH
# See COPYING for details.

"""
Functions and types that implement snapshots
"""
from __future__ import print_function

import time
import json

from itertools import count

import attr

from twisted.internet.defer import (
    inlineCallbacks,
    returnValue,
)

from .common import (
    get_node_url,
)

from twisted.web.client import (
    Agent,
    readBody,
)

from twisted.web.http import (
    OK,
    CREATED,
)

from treq.client import (
    HTTPClient,
)

from hyperlink import (
    DecodedURL,
)

from .common import (
    bad_response,
)


# version of the snapshot scheme
SNAPSHOT_VERSION = 1

@inlineCallbacks
def tahoe_put_immutable(nodeurl, filepath, treq):
    """
    :param DecodedURL nodeurl: The web endpoint of the Tahoe-LAFS client
        associated with the magic-folder client.
    :param FilePath filepath: The file path that needs to be stored into
        the grid.
    :param HTTPClient treq: An ``HTTPClient`` or similar object to use to
        make the queries.
    :return Deferred[unicode]: The readcap associated with the newly created
        unlinked file.
    """
    url = nodeurl.child(
        u"uri",
    ).add(
        u"format",
        u"CHK",
    )

    put_uri = url.to_uri().to_text().encode("ascii")
    # XXX: Should not read entire file into memory. See:
    # https://github.com/LeastAuthority/magic-folder/issues/129
    with filepath.open("r") as file:
        data = file.read()

    response = yield treq.put(put_uri, data)
    if response.code == OK or response.code == CREATED:
        result = yield readBody(response)
        returnValue(result)
    else:
        raise Exception("Error response PUT {} - {}".format(put_uri, response))

@inlineCallbacks
def tahoe_create_snapshot_dir(nodeurl, content, parents, timestamp, treq):
    """
    :param DecodedURL nodeurl: The web endpoint of the Tahoe-LAFS client
        associated with the magic-folder client.
    :param unicode content: readcap for the content.
    :param [unicode] parents: List of parent snapshot caps
    :param integer timestamp: POSIX timestamp that represents the creation time
    :return Deferred[unicode]: The readcap associated with the newly created
        snapshot.
    """

    # dict that would be serialized to JSON
    body = \
    {
        u"content": [ "filenode", { u"ro_uri": content,
                                    u"metadata": { } } ],
        u"version": [ "filenode", { u"ro_uri": str(SNAPSHOT_VERSION),
                                    u"metadata": { } } ],
        u"timestamp": [ "filenode", { u"ro_uri": str(timestamp),
                                      u"metadata": { } } ],
    }

    # populate parents
    # The goal is to populate the dictionary with keys u"parent0", u"parent1" ...
    # with corresponding dirnode values that point to the parent URIs.
    if parents != []:
        for (i, p) in enumerate(parents):
            body[unicode("parent" + str(i), 'utf-8')] = [ "dirnode", { u"ro_uri": p } ]

    body_json = json.dumps(body)

    # POST /uri?t=mkdir-immutable
    url = nodeurl.child(
        u"uri",
    ).add(
        u"t",
        u"mkdir-immutable"
    )

    post_uri = url.to_uri().to_text().encode("ascii")
    response = yield treq.post(post_uri, body_json)
    if response.code != OK:
        returnValue((yield bad_response(url, response)))

    result = yield readBody(response)
    returnValue(result)


# Dev steps
# 1. Finish SnapshotMetadata in-memory representation and simple logic
# 2. upload SnapshotMetadata to grid, download again
# 3. insert SnapshotMetadata into local database, retrieve again
# 4.


@attr.s
class SnapshotMetadata(object):
    parent_caps = attr.ib()
    content_cap = attr.ib()
    timestamp = attr.ib()

    def serialize(self):
        return {
            "parent0": ...,
        }

    @classmethod
    def unserialize(cls, serialized):
        return cls(
            serialized["parent0"],
            ...
        )

    # @classmethod
    # def from_row(cls, row):
    #     # ...


    def is_parent_of(cls, snapshot):
        # walk parent pointers

# list local state
#   foo -> 000001
#   bar -> 000002
#   baz -> 000003

# foo = Snapshot.unserialize(read_object(000001))
# bar = Snapshot.unserialize(read_object(000002))
# baz = Snapshot.unserialize(read_object(000003))



# list /collective/my_folder
#   foo -> 000001
#   bar -> 000002
#   baz -> 000004

# list /collective/your_folder
#   foo -> 000001
#   bar -> 000002
#   baz -> 000005


# local_baz.is_parent_of(my_baz) -> True
#   fast_forward(local_checkout_directory, local_baz, my_baz)

# my_baz.is_parent_of(your_baz) -> False
# your_baz.is_parent_of(my_baz) -> True
#     do nothing

# your_baz.is_parent_of(my_baz) -> False
#     create_local_conflict_state(local_checkout_directory, my_baz, your_baz)


# inotify says foo changed
# upload_content(local_checkout_directory, local_foo)
        # tahoe put .../local_foo ..../grid_foo
        #    -> CHK:000001
        #    -> unchanged, don't upload new snapshot

# local foo -> 000007
# my    foo -> 000008
# inotify says foo changed
        # can't upload, diverged

@attr.s
class Snapshot(object):
    """
    Represents a snapshot corresponding to a file.
    """
    filepath = attr.ib()
    node_directory = attr.ib(converter=lambda p: p.asBytesMode())

    @inlineCallbacks
    def create_snapshot(self, parents, treq):
        """
        Create a snapshot.

        :param [unicode] parents: List of parent snapshots of the current snapshot
            (read-caps of parent snapshots)

        :param HTTPClient treq: An ``HTTPClient`` or similar object to use to
            make the queries.

        :return Deferred[unicode]: Snapshot read-only cap is returned on success.
            Otherwise an appropriate exception is raised.
        """

        nodeurl_u = unicode(get_node_url(self.node_directory.path), 'utf-8')
        nodeurl = DecodedURL.from_text(nodeurl_u)

        content_cap = yield tahoe_put_immutable(nodeurl, self.filepath, treq)

        now = time.time()

        # HTTP POST mkdir-immutable
        snapshot_cap = yield tahoe_create_snapshot_dir(nodeurl,
                                                       content_cap,
                                                       parents,
                                                       now,
                                                       treq)

        returnValue(snapshot_cap)
