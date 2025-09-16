"""
Base repository implementation for data access layer with read/write splitting
"""

from typing import TypeVar, Generic, Type, List, Optional, Any, Dict, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.error_handler import handle_db_errors, with_retry
from database.read_write_manager import get_read_session, get_write_session

# Generic type for models
T = TypeVar('T')

class BaseRepository(Generic[T]):
    """
    Base repository class implementing common data access operations
    
    This class provides a standardized interface for database operations
    following the repository pattern with read/write splitting support.
    """
    
    def __init__(self, model_class: Type[T], session: Session):
        """
        Initialize repository
        
        Args:
            model_class: SQLAlchemy model class
            session: SQLAlchemy database session
        """
        self.model_class = model_class
        self.session = session
    
    @classmethod
    def for_read(cls, model_class: Type[T]) -> 'BaseRepository[T]':
        """
        Create repository instance for read operations
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            Repository instance with read session
        """
        return cls(model_class, get_read_session())
    
    @classmethod
    def for_write(cls, model_class: Type[T]) -> 'BaseRepository[T]':
        """
        Create repository instance for write operations
        
        Args:
            model_class: SQLAlchemy model class
            
        Returns:
            Repository instance with write session
        """
        return cls(model_class, get_write_session())
    
    @handle_db_errors
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        Get entity by ID
        
        Args:
            id: Primary key value
            
        Returns:
            Entity if found, None otherwise
        """
        return self.session.query(self.model_class).get(id)
    
    @handle_db_errors
    def get_all(self) -> List[T]:
        """
        Get all entities
        
        Returns:
            List of all entities
        """
        return self.session.query(self.model_class).all()
    
    @handle_db_errors
    def find(self, **kwargs) -> List[T]:
        """
        Find entities by attributes
        
        Args:
            **kwargs: Attribute filters
            
        Returns:
            List of matching entities
        """
        return self.session.query(self.model_class).filter_by(**kwargs).all()
    
    @handle_db_errors
    def find_one(self, **kwargs) -> Optional[T]:
        """
        Find single entity by attributes
        
        Args:
            **kwargs: Attribute filters
            
        Returns:
            Matching entity if found, None otherwise
        """
        return self.session.query(self.model_class).filter_by(**kwargs).first()
    
    @handle_db_errors
    def create(self, **kwargs) -> T:
        """
        Create new entity
        
        Args:
            **kwargs: Entity attributes
            
        Returns:
            Created entity
        """
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity
    
    @handle_db_errors
    def update(self, id: Any, **kwargs) -> Optional[T]:
        """
        Update entity by ID
        
        Args:
            id: Primary key value
            **kwargs: Attributes to update
            
        Returns:
            Updated entity if found, None otherwise
        """
        entity = self.get_by_id(id)
        if entity:
            for key, value in kwargs.items():
                setattr(entity, key, value)
            self.session.commit()
            self.session.refresh(entity)
        return entity
    
    @handle_db_errors
    def delete(self, id: Any) -> bool:
        """
        Delete entity by ID
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False
    
    @handle_db_errors
    def count(self, **kwargs) -> int:
        """
        Count entities matching criteria
        
        Args:
            **kwargs: Attribute filters
            
        Returns:
            Count of matching entities
        """
        return self.session.query(self.model_class).filter_by(**kwargs).count()
    
    @handle_db_errors
    def exists(self, **kwargs) -> bool:
        """
        Check if entity exists
        
        Args:
            **kwargs: Attribute filters
            
        Returns:
            True if exists, False otherwise
        """
        return self.count(**kwargs) > 0
    
    @handle_db_errors
    def bulk_create(self, entities: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple entities
        
        Args:
            entities: List of entity attribute dictionaries
            
        Returns:
            List of created entities
        """
        created = []
        for entity_data in entities:
            entity = self.model_class(**entity_data)
            self.session.add(entity)
            created.append(entity)
        
        self.session.commit()
        for entity in created:
            self.session.refresh(entity)
        
        return created
    
    @handle_db_errors
    def bulk_update(self, ids: List[Any], **kwargs) -> int:
        """
        Update multiple entities by IDs
        
        Args:
            ids: List of primary key values
            **kwargs: Attributes to update
            
        Returns:
            Number of updated entities
        """
        query = self.session.query(self.model_class).filter(
            self.model_class.id.in_(ids)
        )
        count = query.update(kwargs, synchronize_session=False)
        self.session.commit()
        return count
    
    @handle_db_errors
    def bulk_delete(self, ids: List[Any]) -> int:
        """
        Delete multiple entities by IDs
        
        Args:
            ids: List of primary key values
            
        Returns:
            Number of deleted entities
        """
        query = self.session.query(self.model_class).filter(
            self.model_class.id.in_(ids)
        )
        count = query.delete(synchronize_session=False)
        self.session.commit()
        return count