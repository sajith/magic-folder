import io
import os

from twisted.internet import defer
from twisted.python.filepath import (
    FilePath,
)
from twisted.web.resource import (
    Resource,
)
from twisted.web.client import (
    Agent,
    FileBodyProducer,
)

from treq.client import (
    HTTPClient,
)
from treq.testing import (
    RequestTraversalAgent,
    RequestSequence,
    StubTreq,
)

from testtools.matchers import (
    StartsWith,
)

from magic_folder.snapshot import create_snapshot

from .fixtures import (
    NodeDirectory,
)
from .common import (
    ShouldFailMixin,
    SyncTestCase,
    AsyncTestCase,
    skipIf,
)


class _FakeTahoeRoot(Resource):
    """
    This is a sketch of how an in-memory 'fake' of a Tahoe
    WebUI. Ultimately, this will live in Tahoe
    """


class _FakeTahoeUriHandler(Resource):
    """
    """

    isLeaf = True

    def render(self, request):
        return b"URI:DIR2-CHK:some capability"


def create_fake_tahoe_root():
    """
    Probably should take some params to control what this fake does:
    return errors, pre-populate capabilities, ...
    """
    root = _FakeTahoeRoot()
    root.putChild(
        b"uri",
        _FakeTahoeUriHandler(),
    )
    return root



class TahoeSnapshotTest(AsyncTestCase):
    """
    Tests for the snapshots
    """

    @defer.inlineCallbacks
    def setUp(self):
        """
        Create a Tahoe-LAFS node which contain some magic-folder configuration
        and run it.
        """
        yield super(TahoeSnapshotTest, self).setUp()
        self._nodedir = self.useFixture(
            NodeDirectory(
                path=FilePath(self.mktemp()),
            )
        )
        self._root = create_fake_tahoe_root()
        self._agent = RequestTraversalAgent(self._root)
        self._client = HTTPClient(
            self._agent,
            data_to_body_producer=_SynchronousProducer,
        )

    @defer.inlineCallbacks
    def test_create_new_tahoe_snapshot(self):
        """
        create a new snapshot (this will have no parent snapshots).
        """

        # Get a magic folder.
        folder_path = self._nodedir.path.child(u"magic-folder")

        os.mkdir(folder_path.asBytesMode().path)
        file_path = folder_path.child("foo")
        file_path.touch()

        # XXX THINK: do we really need a full node-dir ?
        snapshot = yield create_snapshot(
            node_directory=self._nodedir.path,
            filepath=file_path,
            parents=[],
            treq=self._client,
        )

        self.assertThat(snapshot.capability, StartsWith("URI:DIR2-CHK:"))