from typing import Any, Generic, TypeVar

from core.repositories.base import BaseRepository

RepoT = TypeVar('RepoT', bound=BaseRepository)


class BaseService(Generic[RepoT]):
    """Application service base — receives repository via constructor (DI)."""

    repository_class: type[RepoT] | None = None

    def __init__(self, repository: RepoT | None = None):
        if repository is not None:
            self.repository = repository
        elif self.repository_class is not None:
            self.repository = self.repository_class()
        else:
            raise ValueError(f'{self.__class__.__name__} requires repository_class or repository')

    def get(self, id: int):
        instance = self.repository.get_by_id(id)
        if instance is None:
            from core.exceptions import NotFoundAppError

            raise NotFoundAppError(f'Record {id} not found')
        return instance

    def create(self, data: dict[str, Any]):
        return self.repository.create(data)

    def update(self, id: int, data: dict[str, Any]):
        instance = self.get(id)
        return self.repository.update(instance, data)

    def delete(self, id: int):
        instance = self.get(id)
        self.repository.delete(instance)

    def list_all(self):
        return self.repository.get_all()
