# -*- encoding: utf-8

import abc
import contextlib
import json
import pathlib
import tempfile

import pytest

from storage import JsonObjectStore, MemoryObjectStore, NoSuchObject, ObjectStore


class ObjectStoreTestCasesMixin(abc.ABC):
    @abc.abstractmethod
    @contextlib.contextmanager
    def create_store(self, initial_objects):
        pass

    def test_can_get_objects(self):
        with self.create_store(initial_objects={"1": "one", "2": "two"}) as s:
            assert s.get(obj_id="1") == "one"
            assert s.get(obj_id="2") == "two"

            with pytest.raises(NoSuchObject):
                s.get(obj_id="3")

    @pytest.mark.parametrize(
        "obj_data",
        ["one", 1, None, {"es": "uno"}, ["a", "b", "c"]]
    )
    def test_can_put_objects(self, obj_data):
        with self.create_store(initial_objects={}) as s:
            s.put(obj_id="1", obj_data=obj_data)

    @pytest.mark.parametrize("obj_id", [1, None, object])
    def test_can_only_put_object_id_str(self, obj_id):
        with self.create_store(initial_objects={}) as s:
            with pytest.raises(TypeError):
                s.put(obj_id=obj_id, obj_data="one")

    @pytest.mark.parametrize("initial_value, updated_value", [
        ("one", "two"),
        (1, 2),
        (None, "None"),
        ({"es": "uno"}, {"de": "eins"}),
        (["a", "b", "c"], ["a", "b", "c", "d", "e"]),
        (("cat", "dog"), ("cat", "dog", "fox")),
    ])
    def test_is_consistent(self, initial_value, updated_value):
        with self.create_store(initial_objects={}) as s:
            with pytest.raises(NoSuchObject):
                s.get(obj_id="1")

            s.put(obj_id="1", obj_data=initial_value)
            assert s.get(obj_id="1") == initial_value

            s.put(obj_id="1", obj_data=updated_value)
            assert s.get(obj_id="1") == updated_value


class TestMemoryObjectStore(ObjectStoreTestCasesMixin):
    @contextlib.contextmanager
    def create_store(self, initial_objects):
        yield MemoryObjectStore(initial_objects=initial_objects)


class TestJsonObjectStore(ObjectStoreTestCasesMixin):
    @contextlib.contextmanager
    def create_store(self, initial_objects):
        _, temp_path = tempfile.mkstemp()
        path = pathlib.Path(temp_path)
        path.write_text(json.dumps(initial_objects))

        yield JsonObjectStore(path)

        path.unlink()
