import io
import os
from tempfile import mktemp
from shutil import rmtree

from testtools.matchers import (
    Equals,
    MatchesStructure,
    Always,
)

from testtools.twistedsupport import (
    succeeded,
)

from hypothesis import (
    given,
)
from hypothesis.strategies import (
    binary,
)

from twisted.python.filepath import (
    FilePath,
)

from allmydata.node import (
    read_config,
)

from .fixtures import (
    NodeDirectory,
)
from .common import (
    SyncTestCase,
)
from .strategies import (
    magic_folder_filenames,
)
from magic_folder.snapshot import (
    create_local_author,
    create_local_author_from_config,
    write_local_author,
    create_snapshot,
)


class TestLocalAuthor(SyncTestCase):
    """
    Functionaltiy of LocalAuthor instances
    """

    def setUp(self):
        d = super(TestLocalAuthor, self).setUp()
        magic_dir = FilePath(mktemp())
        self.node = self.useFixture(NodeDirectory(FilePath(mktemp())))
        self.node.create_magic_folder(
            u"default",
            u"URI:CHK2:{}:{}:1:1:256".format(u"a"*16, u"a"*32),
            u"URI:CHK2:{}:{}:1:1:256".format(u"b"*16, u"b"*32),
            magic_dir,
            60,
        )

        self.config = read_config(self.node.path.path, "portnum")

        return d

    def test_serialize_author(self):
        """
        Write and then read a LocalAuthor to our node-directory
        """
        alice = create_local_author("alice")
        self.assertThat(alice.name, Equals("alice"))

        # serialize the author to disk
        write_local_author(alice, "default", self.config)

        # read back the author
        alice2 = create_local_author_from_config(self.config)
        self.assertThat(
            alice2,
            MatchesStructure(
                name=Equals("alice"),
                verify_key=Equals(alice.verify_key),
            )
        )


class TestLocalSnapshot(SyncTestCase):
    """
    Test functionality of LocalSnapshot, the in-memory version of Snapshots.
    """

    def setUp(self):
        self.alice = create_local_author("alice")
        self.stash_dir = mktemp()
        os.mkdir(self.stash_dir)
        return super(TestLocalSnapshot, self).setUp()

    def tearDown(self):
        rmtree(self.stash_dir)
        return super(TestLocalSnapshot, self).tearDown()

    @given(
        content=binary(min_size=1),
        filename=magic_folder_filenames(),
    )
    def test_create_new_tahoe_snapshot(self, content, filename):
        """
        create a new snapshot (this will have no parent snapshots).
        """
        data = io.BytesIO(content)

        snapshots = []
        d = create_snapshot(
            name=filename,
            author=self.alice,
            data_producer=data,
            snapshot_stash_dir=self.stash_dir,
            parents=[],
        )
        d.addCallback(snapshots.append)
        self.assertThat(
            d,
            succeeded(Always()),
        )
        # we should assert some stuff about snapshots[0] now

    @given(
        content1=binary(min_size=1),
        content2=binary(min_size=1),
        filename=magic_folder_filenames(),
    )
    def test_create_local_snapshots(self, content1, content2, filename):
        """
        Create a local snapshot and then change the content of the file
        to make another snapshot.
        """
        data1 = io.BytesIO(content1)
        parents = []

        d = create_snapshot(
            name=filename,
            author=self.alice,
            data_producer=data1,
            snapshot_stash_dir=self.stash_dir,
        )
        d.addCallback(parents.append)
        self.assertThat(
            d,
            succeeded(Always()),
        )

        data2 = io.BytesIO(content2)
        d = create_snapshot(
            name=filename,
            author=self.alice,
            data_producer=data2,
            snapshot_stash_dir=self.stash_dir,
            parents=parents,
        )
        d.addCallback(parents.append)
        self.assertThat(
            d,
            succeeded(Always()),
        )

    @given(
        content1=binary(min_size=1),
        content2=binary(min_size=1),
        filename=magic_folder_filenames(),
    )
    def test_snapshots_with_parents(self, content1, content2, filename):
        """
        Create a local snapshot, commit it to the grid, then extend that
        with another local snapshot and again commit it with the previously
        created remote snapshot as the parent. Now, fetch the remote from the
        capability string and compare parent to see if they match.
        """
        data1 = io.BytesIO(content1)
        local_snapshots = []

        # create a local snapshot and commit it to the grid
        d = create_snapshot(
            name=filename,
            author=self.alice,
            data_producer=data1,
            snapshot_stash_dir=self.stash_dir,
            parents=[],
        )
        d.addCallback(local_snapshots.append)
        self.assertThat(
            d,
            succeeded(Always()),
        )

        # now modify the same file and create a new local snapshot
        data2 = io.BytesIO(content2)
        d = create_snapshot(
            name=filename,
            author=self.alice,
            data_producer=data2,
            snapshot_stash_dir=self.stash_dir,
            parents=local_snapshots[0],
        )

        d.addCallback(local_snapshots.append)
        self.assertThat(
            d,
            succeeded(Always()),
        )
