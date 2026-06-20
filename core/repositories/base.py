from typing import Any, Generic, TypeVar

from django.db import models

ModelT = TypeVar('ModelT', bound=models.Model)


class BaseRepository(Generic[ModelT]):
    """Generic data-access layer. Subclasses set `model_class`."""

    model_class: type[ModelT] | None = None

    def __init__(self, model_class: type[ModelT] | None = None):
        if model_class is not None:
            self.model_class = model_class
        if self.model_class is None:
            raise ValueError(f'{self.__class__.__name__} requires model_class')

    def get_queryset(self):
        return self.model_class.objects.all()

    def get_by_id(self, id: int) -> ModelT | None:
        try:
            return self.get_queryset().get(pk=id)
        except self.model_class.DoesNotExist:
            return None

    def get_all(self):
        return list(self.get_queryset())

    def create(self, data: dict[str, Any]) -> ModelT:
        return self.model_class.objects.create(**data)

    def update(self, instance: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def delete(self, instance: ModelT) -> None:
        instance.delete()

    def filter(self, **kwargs):
        return self.get_queryset().filter(**kwargs)

    def first(self, **kwargs) -> ModelT | None:
        return self.get_queryset().filter(**kwargs).first()

    def count(self, **kwargs) -> int:
        return self.get_queryset().filter(**kwargs).count()

    def exists(self, **kwargs) -> bool:
        return self.get_queryset().filter(**kwargs).exists()
