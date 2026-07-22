from whitenoise.storage import CompressedManifestStaticFilesStorage

class CustomWhiteNoiseStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False
    
    def __init__(self, *args, **kwargs):
        # Django 4.2+ passes manifest_strict=True by default to ManifestStaticFilesStorage
        # We pop it out if it exists, or just overwrite it after super()
        kwargs.pop("manifest_strict", None)
        super().__init__(*args, **kwargs)
        self.manifest_strict = False
