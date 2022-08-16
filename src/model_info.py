#  Copyright (c) 2022. DataRobot, Inc. and its affiliates.
#  All rights reserved.
#  This is proprietary source code of DataRobot, Inc. and its affiliates.
#  Released under the terms of DataRobot Tool and Utility Agreement.

"""
A module that contains information about a model that was scanned and loaded from the local
source tree.
"""

import logging
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict
from typing import List

from model_file_path import ModelFilePath
from schema_validator import ModelSchema

logger = logging.getLogger()


class ModelInfo:
    """Holds information about a model from the local source tree."""

    _model_file_paths: Dict[Path, ModelFilePath]

    @dataclass
    class Flags:
        """Contains flags to indicate certain conditions."""

        should_upload_all_files: bool = False
        should_update_settings: bool = False

    @dataclass
    class FileChanges:
        """Contains lists of changed/new and deleted files."""

        changed_or_new_files: List[ModelFilePath] = field(default_factory=list)
        deleted_file_ids: List[str] = field(default_factory=list)

        def add_changed(self, model_file_path):
            """Add model file to the changes/new list."""

            self.changed_or_new_files.append(model_file_path)

        def extend_deleted(self, deleted_file_id_list):
            """EXtend the delete file IDs list."""

            self.deleted_file_ids.extend(deleted_file_id_list)

    def __init__(self, yaml_filepath, model_path, metadata):
        self._yaml_filepath = Path(yaml_filepath)
        self._model_path = Path(model_path)
        self._metadata = metadata
        self._model_file_paths = {}
        self.file_changes = self.FileChanges()
        self.flags = self.Flags()

    @property
    def yaml_filepath(self):
        """The yaml file path from which the given model metadata definition was read from"""
        return self._yaml_filepath

    @property
    def model_path(self):
        """The model's root directory"""
        return self._model_path

    @property
    def metadata(self):
        """The model's metadata"""
        return self._metadata

    @property
    def user_provided_id(self):
        """A model's unique ID that is provided by the user and read from the model's metadata"""
        return self.metadata[ModelSchema.MODEL_ID_KEY]

    @property
    def model_file_paths(self):
        """A list of file paths that associated with the given model"""
        return self._model_file_paths

    @property
    def is_binary(self):
        """Whether the given model's target type is binary"""
        return ModelSchema.is_binary(self.metadata)

    @property
    def is_regression(self):
        """Whether the given model's target type is regression"""
        return ModelSchema.is_regression(self.metadata)

    @property
    def is_unstructured(self):
        """Whether the given model's target type is unstructured"""
        return ModelSchema.is_unstructured(self.metadata)

    @property
    def is_multiclass(self):
        """Whether the given model's target type is multi-class"""
        return ModelSchema.is_multiclass(self.metadata)

    def main_program_filepath(self):
        """Returns the main program file path of the given model"""
        try:
            return next(p for _, p in self.model_file_paths.items() if p.name == "custom.py")
        except StopIteration:
            return None

    def main_program_exists(self):
        """Returns whether the main program file path exists or not"""
        return self.main_program_filepath() is not None

    def set_model_paths(self, paths, repo_root_path):
        """
        Builds a dictionary of the files belong to the given model. The key is a resolved
        file path of a given file and the value is a ModelFilePath of that same file.

        Parameters
        ----------
        paths : list
            A list of file paths associated with the given model.
        repo_root_path : pathlib.Path
            The repository root directory.
        """

        logger.debug("Model %s is set with the following paths: %s", self.user_provided_id, paths)
        self._model_file_paths = {}
        for path in paths:
            model_filepath = ModelFilePath(path, self.model_path, repo_root_path)
            self._model_file_paths[model_filepath.resolved] = model_filepath

    def paths_under_model_by_relative(self, relative_to):
        """
        Returns a list (as a set) of the model's files that subjected to specific relative value.

        Parameters
        ----------
        relative_to : ModelFilePath.RelativeTo
            The relation value.

        Returns
        -------
        set,
            The list of the model's that subjected to the given input relative value.
        """

        return set(
            p.under_model for _, p in self.model_file_paths.items() if p.relative_to == relative_to
        )

    @property
    def is_affected_by_commit(self):
        """Whether the given model is affected by the last commit"""
        return self.should_create_new_version or self.flags.should_update_settings

    @property
    def should_create_new_version(self):
        """Whether a new custom inference model version should be created"""
        return (
            self.flags.should_upload_all_files
            or self.file_changes.changed_or_new_files
            or self.get_value(ModelSchema.VERSION_KEY, ModelSchema.MEMORY_KEY)
            or self.get_value(ModelSchema.VERSION_KEY, ModelSchema.REPLICAS_KEY)
        )

    @property
    def should_run_test(self):
        """
        Querying the model's metadata and check whether a custom model testing should be executed.
        """
        return ModelSchema.TEST_KEY in self.metadata and not self.get_value(
            ModelSchema.TEST_KEY, ModelSchema.TEST_SKIP_KEY
        )

    def get_value(self, key, *sub_keys):
        """
        Get a value from the model's metadata given a key and sub-keys.

        Parameters
        ----------
        key : str
            A key name from the ModelSchema.
        sub_keys :
            An optional dynamic sub-keys from the ModelSchema.

        Returns
        -------
        Any or None,
            The value associated with the provided key (and sub-keys) or None if not exists.
        """

        return ModelSchema.get_value(self.metadata, key, *sub_keys)

    def get_settings_value(self, key, *sub_keys):
        """
        Get a value from the model's metadata settings section, given a key and sub-keys under
        the settings section.

        Parameters
        ----------
        key : str
            A key name from the ModelSchema, which is supposed to be under the
            SharedSchema.SETTINGS_SECTION_KEY section.
        sub_keys :
            An optional dynamic sub-keys from the ModelSchema, which are under the
            SharedSchema.SETTINGS_SECTION_KEY section.

        Returns
        -------
        Any or None,
            The value associated with the provided key (and sub-keys) or None if not exists.
        """

        return self.get_value(ModelSchema.SETTINGS_SECTION_KEY, key, *sub_keys)
