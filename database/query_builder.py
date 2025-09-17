"""
Query Builder for complex database queries
Provides a fluent interface for building complex SQL queries
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable
from sqlalchemy import and_, or_, not_, desc, asc, func, text
from sqlalchemy.orm import Query, Session, aliased
from sqlalchemy.sql import expression
from database.read_write_manager import get_read_session, get_write_session
from database.error_handler import handle_db_errors

T = TypeVar('T')

class QueryBuilder:
    """
    Fluent query builder for complex database queries
    
    This class provides a chainable API for building complex queries
    with filtering, sorting, pagination, and aggregation.
    """
    
    def __init__(self, model_class: Type[T], session: Optional[Session] = None, for_write: bool = False):
        """
        Initialize query builder
        
        Args:
            model_class: SQLAlchemy model class
            session: SQLAlchemy session (optional)
            for_write: Whether this query is for write operations
        """
        self.model_class = model_class
        self._session = session
        self._for_write = for_write
        self._query = None
        self._filters = []
        self._order_by = []
        self._group_by = []
        self._limit = None
        self._offset = None
        self._joins = []
        self._having = []
        self._select_fields = []
        self._distinct = False
        self._count_only = False
        self._subqueries = {}
        self._aliases = {}
    
    @property
    def session(self) -> Session:
        """Get or create session based on operation type"""
        if self._session:
            return self._session
        
        if self._for_write:
            return get_write_session()
        return get_read_session()
    
    @classmethod
    def read(cls, model_class: Type[T], session: Optional[Session] = None) -> 'QueryBuilder':
        """Create query builder for read operations"""
        return cls(model_class, session, for_write=False)
    
    @classmethod
    def write(cls, model_class: Type[T], session: Optional[Session] = None) -> 'QueryBuilder':
        """Create query builder for write operations"""
        return cls(model_class, session, for_write=True)
    
    def _build_query(self) -> Query:
        """Build SQLAlchemy query from builder state"""
        # Start with base query
        if self._select_fields:
            query = self.session.query(*self._select_fields)
        else:
            query = self.session.query(self.model_class)
        
        # Apply distinct if needed
        if self._distinct:
            query = query.distinct()
        
        # Apply joins
        for join_info in self._joins:
            target = join_info['target']
            condition = join_info.get('condition')
            isouter = join_info.get('isouter', False)
            
            if condition:
                query = query.join(target, condition, isouter=isouter)
            else:
                query = query.join(target, isouter=isouter)
        
        # Apply filters
        if self._filters:
            query = query.filter(and_(*self._filters))
        
        # Apply group by
        if self._group_by:
            query = query.group_by(*self._group_by)
        
        # Apply having
        if self._having:
            query = query.having(and_(*self._having))
        
        # Apply order by
        for order_info in self._order_by:
            column = order_info['column']
            direction = order_info['direction']
            query = query.order_by(direction(column))
        
        # Apply limit and offset
        if self._limit is not None:
            query = query.limit(self._limit)
        
        if self._offset is not None:
            query = query.offset(self._offset)
        
        return query
    
    def select(self, *fields) -> 'QueryBuilder':
        """
        Select specific fields
        
        Args:
            *fields: Fields to select
            
        Returns:
            Self for chaining
        """
        self._select_fields.extend(fields)
        return self
    
    def distinct(self) -> 'QueryBuilder':
        """
        Make query return distinct results
        
        Returns:
            Self for chaining
        """
        self._distinct = True
        return self
    
    def filter(self, *conditions) -> 'QueryBuilder':
        """
        Add filter conditions
        
        Args:
            *conditions: SQLAlchemy filter conditions
            
        Returns:
            Self for chaining
        """
        self._filters.extend(conditions)
        return self
    
    def filter_by(self, **kwargs) -> 'QueryBuilder':
        """
        Add equality filters
        
        Args:
            **kwargs: Field-value pairs
            
        Returns:
            Self for chaining
        """
        for key, value in kwargs.items():
            self._filters.append(getattr(self.model_class, key) == value)
        return self
    
    def join(self, target, condition=None, isouter=False) -> 'QueryBuilder':
        """
        Add join to query
        
        Args:
            target: Join target
            condition: Join condition
            isouter: Whether to use outer join
            
        Returns:
            Self for chaining
        """
        self._joins.append({
            'target': target,
            'condition': condition,
            'isouter': isouter
        })
        return self
    
    def left_join(self, target, condition=None) -> 'QueryBuilder':
        """
        Add left outer join to query
        
        Args:
            target: Join target
            condition: Join condition
            
        Returns:
            Self for chaining
        """
        return self.join(target, condition, isouter=True)
    
    def order_by(self, column, ascending=True) -> 'QueryBuilder':
        """
        Add order by clause
        
        Args:
            column: Column to order by
            ascending: Whether to sort ascending
            
        Returns:
            Self for chaining
        """
        direction = asc if ascending else desc
        self._order_by.append({
            'column': column,
            'direction': direction
        })
        return self
    
    def group_by(self, *columns) -> 'QueryBuilder':
        """
        Add group by clause
        
        Args:
            *columns: Columns to group by
            
        Returns:
            Self for chaining
        """
        self._group_by.extend(columns)
        return self
    
    def having(self, *conditions) -> 'QueryBuilder':
        """
        Add having clause
        
        Args:
            *conditions: Having conditions
            
        Returns:
            Self for chaining
        """
        self._having.extend(conditions)
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder':
        """
        Set result limit
        
        Args:
            limit: Maximum number of results
            
        Returns:
            Self for chaining
        """
        self._limit = limit
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder':
        """
        Set result offset
        
        Args:
            offset: Result offset
            
        Returns:
            Self for chaining
        """
        self._offset = offset
        return self
    
    def paginate(self, page: int, page_size: int) -> 'QueryBuilder':
        """
        Set pagination
        
        Args:
            page: Page number (1-based)
            page_size: Page size
            
        Returns:
            Self for chaining
        """
        self._offset = (page - 1) * page_size
        self._limit = page_size
        return self
    
    def alias(self, model_class, alias_name: str) -> Any:
        """
        Create alias for model class
        
        Args:
            model_class: Model class to alias
            alias_name: Alias name
            
        Returns:
            Aliased model class
        """
        if alias_name not in self._aliases:
            self._aliases[alias_name] = aliased(model_class)
        return self._aliases[alias_name]
    
    def subquery(self, name: str, builder: 'QueryBuilder') -> Any:
        """
        Add subquery
        
        Args:
            name: Subquery name
            builder: Query builder for subquery
            
        Returns:
            Subquery object
        """
        if name not in self._subqueries:
            self._subqueries[name] = builder._build_query().subquery(name)
        return self._subqueries[name]
    
    def count(self) -> int:
        """
        Count results
        
        Returns:
            Result count
        """
        query = self._build_query()
        return query.count()
    
    @handle_db_errors
    def all(self) -> List[T]:
        """
        Execute query and get all results
        
        Returns:
            List of results
        """
        query = self._build_query()
        return query.all()
    
    @handle_db_errors
    def first(self) -> Optional[T]:
        """
        Execute query and get first result
        
        Returns:
            First result or None
        """
        query = self._build_query()
        return query.first()
    
    @handle_db_errors
    def one_or_none(self) -> Optional[T]:
        """
        Execute query and get one result or None
        
        Returns:
            Single result or None
        """
        query = self._build_query()
        return query.one_or_none()
    
    @handle_db_errors
    def scalar(self) -> Any:
        """
        Execute query and get scalar result
        
        Returns:
            Scalar result
        """
        query = self._build_query()
        return query.scalar()
    
    def exists(self) -> bool:
        """
        Check if query returns any results
        
        Returns:
            True if results exist, False otherwise
        """
        return self.first() is not None
    
    def to_query(self) -> Query:
        """
        Convert to SQLAlchemy query
        
        Returns:
            SQLAlchemy query object
        """
        return self._build_query()
    
    def union(self, other: 'QueryBuilder') -> Query:
        """
        Create union with another query
        
        Args:
            other: Other query builder
            
        Returns:
            Union query
        """
        return self._build_query().union(other._build_query())
    
    def union_all(self, other: 'QueryBuilder') -> Query:
        """
        Create union all with another query
        
        Args:
            other: Other query builder
            
        Returns:
            Union all query
        """
        return self._build_query().union_all(other._build_query())


# Example usage:
"""
# Create a query builder for read operations
query = QueryBuilder.read(User)

# Build complex query
results = (query
    .select(User.id, User.name, func.count(Post.id).label('post_count'))
    .join(Post, User.id == Post.user_id)
    .filter(User.active == True)
    .group_by(User.id, User.name)
    .having(func.count(Post.id) > 5)
    .order_by(User.name)
    .paginate(page=2, page_size=10)
    .all())
"""