# -*- coding: utf-8 -*-
from django.core.files.storage import FileSystemStorage

class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name, max_length=None):
        """Returns a filename that's free on the target storage system, and
        available for new content to be written to."""

        # If the filename already exists, remove it as if it was a true file system
        if name:
            self.delete(name)

        return super(OverwriteStorage, self).get_available_name(name, max_length)
