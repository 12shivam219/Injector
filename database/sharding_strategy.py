"""
Sharding Strategy for Future Data Growth
Provides a framework for horizontal partitioning of data across multiple databases
"""

import hashlib
import os
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, Session
from database.error_handler import handle_db_errors, with_retry
from database.encryption import decrypt_connection_string
from database.query_monitor import setup_query_monitoring
from database.adaptive_pool import setup_adaptive_pooling
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import logging
logger = logging.getLogger(__name__)

class ShardingStrategy(Enum):
    """Sharding strategies for data distribution"""
    HASH = "hash"           # Hash-based sharding (e.g., hash(user_id) % num_shards)
    RANGE = "range"         # Range-based sharding (e.g., date ranges, ID ranges)
    DIRECTORY = "directory" # Directory-based sharding (lookup table)
    TENANT = "tenant"       # Tenant-based sharding (one shard per tenant/organization)
    GEOGRAPHY = "geography" # Geography-based sharding (e.g., by country/region)

class ShardingConfig:
    """Configuration for sharding strategy"""
    
    def __init__(
        self,
        strategy: ShardingStrategy,
        shard_key: str,
        num_shards: int = 4,
        shard_map: Optional[Dict[Any, int]] = None,
        range_boundaries: Optional[List[Any]] = None
    ):
        """
        Initialize sharding configuration
        
        Args:
            strategy: Sharding strategy to use
            shard_key: Database column to use as shard key
            num_shards: Number of database shards
            shard_map: Mapping of shard key values to shard IDs (for directory strategy)
            range_boundaries: Boundaries for range-based sharding
        """
        self.strategy = strategy
        self.shard_key = shard_key
        self.num_shards = num_shards
        self.shard_map = shard_map or {}
        self.range_boundaries = range_boundaries or []
    
    def get_shard_id(self, key_value: Any) -> int:
        """
        Determine shard ID for a given key value
        
        Args:
            key_value: Value of the shard key
            
        Returns:
            Shard ID (0-based)
        """
        if self.strategy == ShardingStrategy.HASH:
            # Hash-based sharding
            if isinstance(key_value, str):
                hash_value = int(hashlib.md5(key_value.encode()).hexdigest(), 16)
            else:
                hash_value = hash(key_value)
            return hash_value % self.num_shards
        
        elif self.strategy == ShardingStrategy.RANGE:
            # Range-based sharding
            if not self.range_boundaries:
                raise ValueError("Range boundaries must be provided for range-based sharding")
            
            for i, boundary in enumerate(self.range_boundaries):
                if key_value < boundary:
                    return i
            return len(self.range_boundaries)
        
        elif self.strategy == ShardingStrategy.DIRECTORY:
            # Directory-based sharding
            if key_value in self.shard_map:
                return self.shard_map[key_value]
            # Default to hash-based if not in map
            return hash(key_value) % self.num_shards
        
        elif self.strategy == ShardingStrategy.TENANT:
            # Tenant-based sharding (tenant ID is the shard ID)
            if isinstance(key_value, int) and 0 <= key_value < self.num_shards:
                return key_value
            # Default to hash-based if tenant ID is invalid
            return hash(key_value) % self.num_shards
        
        elif self.strategy == ShardingStrategy.GEOGRAPHY:
            # Geography-based sharding
            if isinstance(key_value, str) and key_value in self.shard_map:
                return self.shard_map[key_value]
            # Default to hash-based if region not in map
            return hash(key_value) % self.num_shards
        
        # Default to hash-based sharding
        return hash(key_value) % self.num_shards

class ShardManager:
    """
    Manages database shards and routing
    
    This class provides:
    1. Connection management for multiple database shards
    2. Query routing based on sharding strategy
    3. Cross-shard query execution
    4. Shard rebalancing capabilities
    """
    
    def __init__(
        self,
        config: ShardingConfig,
        connection_strings: List[str] = None,
        min_pool_size: int = 5,
        max_pool_size: int = 20
    ):
        """
        Initialize shard manager
        
        Args:
            config: Sharding configuration
            connection_strings: List of database connection strings (one per shard)
            min_pool_size: Minimum connection pool size per shard
            max_pool_size: Maximum connection pool size per shard
        """
        self.config = config
        self.connection_strings = connection_strings or self._get_connection_strings()
        
        # Ensure we have enough connection strings
        if len(self.connection_strings) < config.num_shards:
            raise ValueError(f"Not enough connection strings provided. "
                            f"Expected {config.num_shards}, got {len(self.connection_strings)}")
        
        # Connection pool settings
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        
        # Initialize engines and sessions
        self.engines = {}
        self.session_factories = {}
        self._initialize_connections()
        
        # Metadata for schema synchronization
        self.metadata = MetaData()
    
    def _get_connection_strings(self) -> List[str]:
        """Get database connection strings from environment"""
        connection_strings = []
        
        # Check if using Neon direct connection
        if os.getenv('USE_NEON_DIRECT', 'false').lower() == 'true':
            # For Neon, we use a single connection string with different database names
            base_conn_str = os.getenv('NEON_CONNECTION_STRING')
            if base_conn_str:
                # Parse the base connection string to extract components
                # Expected format: postgresql://user:pass@host:port/dbname
                parts = base_conn_str.split('/')
                base_url = '/'.join(parts[:-1]) + '/'  # Everything before the database name
                
                # Create connection strings for each shard with different database names
                for i in range(self.config.num_shards):
                    db_name = f"{os.getenv('DB_NAME', 'resume_customizer')}_{i}"
                    shard_conn_str = f"{base_url}{db_name}?sslmode=require"
                    connection_strings.append(shard_conn_str)
                
                return connection_strings
        
        # Check for encrypted connection strings first
        for i in range(self.config.num_shards):
            env_var = f'DB_ENCRYPTED_SHARD_{i}_CONNECTION_STRING'
            encrypted_conn_str = os.getenv(env_var)
            
            if encrypted_conn_str:
                conn_str = decrypt_connection_string(encrypted_conn_str)
                if conn_str:
                    connection_strings.append(conn_str)
                    continue
            
            # Fall back to building from individual credentials
            db_config = {
                'host': os.getenv(f'DB_SHARD_{i}_HOST', os.getenv('DB_HOST', 'localhost')),
                'port': os.getenv(f'DB_SHARD_{i}_PORT', os.getenv('DB_PORT', '5432')),
                'database': os.getenv(f'DB_SHARD_{i}_NAME', f"{os.getenv('DB_NAME', 'resume_customizer')}_{i}"),
                'username': os.getenv(f'DB_SHARD_{i}_USER', os.getenv('DB_USER', 'postgres')),
                'password': os.getenv(f'DB_SHARD_{i}_PASSWORD', os.getenv('DB_PASSWORD', ''))
            }
            
            conn_str = (
                f"postgresql://{db_config['username']}:{db_config['password']}@"
                f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )
            connection_strings.append(conn_str)
        
        return connection_strings
    
    @handle_db_errors
    def _initialize_connections(self):
        """Initialize database connections for all shards"""
        # For Neon, ensure all shard databases exist
        if os.getenv('USE_NEON_DIRECT', 'false').lower() == 'true':
            self._ensure_neon_shard_databases_exist()
            
    def _ensure_neon_shard_databases_exist(self):
        """Create shard databases in Neon PostgreSQL if they don't exist"""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Parse the base connection string to get admin connection
        base_conn_str = os.getenv('NEON_CONNECTION_STRING')
        if not base_conn_str:
            return
            
        try:
            # Connect to default database (postgres)
            parts = base_conn_str.split('/')
            admin_conn_str = '/'.join(parts[:-1]) + '/postgres?sslmode=require'
            
            # Connect and create databases if they don't exist
            conn = psycopg2.connect(admin_conn_str)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            for i in range(self.config.num_shards):
                db_name = f"{os.getenv('DB_NAME', 'resume_customizer')}_{i}"
                # Validate db_name
                import re
                if not re.match(r'^[A-Za-z0-9_\-]+$', db_name):
                    logger.warning("Skipping invalid shard database name: %s", db_name)
                    continue

                # Check if database exists
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                if cursor.fetchone() is None:
                    # Create database if it doesn't exist (safe quoting)
                    try:
                        cursor.execute(f"CREATE DATABASE \"{db_name}\"")
                        logger.info("Created shard database: %s", db_name)
                    except Exception as e:
                        logger.warning("Failed to create shard database %s: %s", db_name, e)
            
            cursor.close()
            conn.close()
        except Exception as e:
            logger.exception("Error ensuring Neon shard databases exist: %s", e)
        for shard_id in range(self.config.num_shards):
            # Check if using Neon PostgreSQL
            if os.getenv('USE_NEON_DIRECT', 'false').lower() == 'true':
                # Optimize connection pooling for Neon's serverless architecture
                engine = create_engine(
                    self.connection_strings[shard_id],
                    pool_size=2,                    # Smaller initial pool for serverless
                    max_overflow=10,                # Allow more overflow connections when needed
                    pool_timeout=30,
                    pool_recycle=300,               # More frequent connection recycling for serverless
                    pool_pre_ping=True,             # Check connection validity before use
                    connect_args={"sslmode": "require"}  # Ensure SSL is used
                )
            else:
                # Standard connection pooling for traditional PostgreSQL
                engine = create_engine(
                    self.connection_strings[shard_id],
                    pool_size=self.min_pool_size,
                    max_overflow=self.max_pool_size - self.min_pool_size,
                    pool_timeout=30,
                    pool_recycle=1800
                )
            
            # Create session factory
            session_factory = sessionmaker(bind=engine)
            
            # Store engine and session factory
            self.engines[shard_id] = engine
            self.session_factories[shard_id] = session_factory
            
            # Set up monitoring and adaptive pooling
            setup_query_monitoring(engine, slow_query_threshold_ms=100)
            setup_adaptive_pooling(
                engine,
                min_pool_size=self.min_pool_size,
                max_pool_size=self.max_pool_size
            )
    
    def get_shard_id(self, key_value: Any) -> int:
        """
        Get shard ID for a given key value
        
        Args:
            key_value: Value of the shard key
            
        Returns:
            Shard ID
        """
        return self.config.get_shard_id(key_value)
    
    def get_session(self, shard_id: int) -> Session:
        """
        Get database session for a specific shard
        
        Args:
            shard_id: Shard ID
            
        Returns:
            Database session
        """
        if shard_id not in self.session_factories:
            raise ValueError(f"Invalid shard ID: {shard_id}")
        
        return self.session_factories[shard_id]()
    
    def get_session_for_key(self, key_value: Any) -> Tuple[Session, int]:
        """
        Get database session for a given key value
        
        Args:
            key_value: Value of the shard key
            
        Returns:
            Tuple of (database session, shard ID)
        """
        shard_id = self.get_shard_id(key_value)
        return self.get_session(shard_id), shard_id
    
    @handle_db_errors
    def execute_on_all_shards(self, callback: Callable[[Session, int], Any]) -> List[Any]:
        """
        Execute a callback on all shards
        
        Args:
            callback: Function to execute on each shard, taking session and shard ID
            
        Returns:
            List of results from each shard
        """
        results = []
        for shard_id in range(self.config.num_shards):
            session = self.get_session(shard_id)
            try:
                result = callback(session, shard_id)
                results.append(result)
            finally:
                session.close()
        return results
    
    @handle_db_errors
    def create_shard_tables(self, base):
        """
        Create tables on all shards
        
        Args:
            base: SQLAlchemy declarative base
        """
        for shard_id, engine in self.engines.items():
            base.metadata.create_all(engine)
    
    def close_all(self):
        """Close all database connections"""
        for engine in self.engines.values():
            engine.dispose()


class ShardedRepository:
    """
    Repository for sharded data access
    
    This class provides:
    1. Transparent data access across shards
    2. Automatic routing of queries to appropriate shards
    3. Cross-shard query capabilities
    """
    
    def __init__(self, model_class, shard_manager: ShardManager, shard_key_field: str):
        """
        Initialize sharded repository
        
        Args:
            model_class: SQLAlchemy model class
            shard_manager: Shard manager
            shard_key_field: Model field used as shard key
        """
        self.model_class = model_class
        self.shard_manager = shard_manager
        self.shard_key_field = shard_key_field
    
    @handle_db_errors
    def get_by_id(self, id: Any, shard_key_value: Any) -> Optional[Any]:
        """
        Get entity by ID and shard key
        
        Args:
            id: Entity ID
            shard_key_value: Value of the shard key
            
        Returns:
            Entity if found, None otherwise
        """
        session, _ = self.shard_manager.get_session_for_key(shard_key_value)
        try:
            return session.query(self.model_class).get(id)
        finally:
            session.close()
    
    @handle_db_errors
    def find_by(self, shard_key_value: Any, **kwargs) -> List[Any]:
        """
        Find entities by attributes on a specific shard
        
        Args:
            shard_key_value: Value of the shard key
            **kwargs: Attribute filters
            
        Returns:
            List of matching entities
        """
        session, _ = self.shard_manager.get_session_for_key(shard_key_value)
        try:
            return session.query(self.model_class).filter_by(**kwargs).all()
        finally:
            session.close()
    
    @handle_db_errors
    def find_across_shards(self, **kwargs) -> List[Any]:
        """
        Find entities by attributes across all shards
        
        Args:
            **kwargs: Attribute filters
            
        Returns:
            List of matching entities from all shards
        """
        def query_shard(session, shard_id):
            return session.query(self.model_class).filter_by(**kwargs).all()
        
        results = []
        shard_results = self.shard_manager.execute_on_all_shards(query_shard)
        for shard_result in shard_results:
            results.extend(shard_result)
        
        return results
    
    @handle_db_errors
    @with_retry
    def create(self, **kwargs) -> Any:
        """
        Create new entity
        
        Args:
            **kwargs: Entity attributes
            
        Returns:
            Created entity
        """
        if self.shard_key_field not in kwargs:
            raise ValueError(f"Shard key field '{self.shard_key_field}' must be provided")
        
        shard_key_value = kwargs[self.shard_key_field]
        session, _ = self.shard_manager.get_session_for_key(shard_key_value)
        
        try:
            entity = self.model_class(**kwargs)
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity
        finally:
            session.close()
    
    @handle_db_errors
    @with_retry
    def update(self, id: Any, shard_key_value: Any, **kwargs) -> Optional[Any]:
        """
        Update entity
        
        Args:
            id: Entity ID
            shard_key_value: Value of the shard key
            **kwargs: Attributes to update
            
        Returns:
            Updated entity if found, None otherwise
        """
        session, _ = self.shard_manager.get_session_for_key(shard_key_value)
        
        try:
            entity = session.query(self.model_class).get(id)
            if entity:
                for key, value in kwargs.items():
                    setattr(entity, key, value)
                session.commit()
                session.refresh(entity)
            return entity
        finally:
            session.close()
    
    @handle_db_errors
    @with_retry
    def delete(self, id: Any, shard_key_value: Any) -> bool:
        """
        Delete entity
        
        Args:
            id: Entity ID
            shard_key_value: Value of the shard key
            
        Returns:
            True if deleted, False if not found
        """
        session, _ = self.shard_manager.get_session_for_key(shard_key_value)
        
        try:
            entity = session.query(self.model_class).get(id)
            if entity:
                session.delete(entity)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @handle_db_errors
    def count_across_shards(self, **kwargs) -> int:
        """
        Count entities across all shards
        
        Args:
            **kwargs: Attribute filters
            
        Returns:
            Total count across all shards
        """
        def count_shard(session, shard_id):
            return session.query(self.model_class).filter_by(**kwargs).count()
        
        shard_counts = self.shard_manager.execute_on_all_shards(count_shard)
        return sum(shard_counts)


# Example usage:
"""
# Define sharding configuration
config = ShardingConfig(
    strategy=ShardingStrategy.HASH,
    shard_key="user_id",
    num_shards=4
)

# Create shard manager
shard_manager = ShardManager(config)

# Create sharded repository
user_repo = ShardedRepository(User, shard_manager, "id")

# Create user (automatically routed to correct shard)
user = user_repo.create(
    id=123,
    name="John Doe",
    email="john@example.com"
)

# Find user by ID (need to provide shard key)
user = user_repo.get_by_id(123, 123)

# Find users across all shards
active_users = user_repo.find_across_shards(active=True)
"""