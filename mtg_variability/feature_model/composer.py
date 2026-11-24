class FeatureModelComposer:

    def compose(
        self,
        base_model: FeatureModel,
        submodels: list[FeatureModel],
    ) -> FeatureModel:
        ...