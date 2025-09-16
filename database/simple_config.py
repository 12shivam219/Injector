"""
Simple database configuration for initial setup
"""
def get_simple_connection_string() -> str:
    """Get a basic PostgreSQL connection string without extra parameters"""
    from urllib.parse import quote_plus
    
    config = {
        'host': 'localhost',
        'port': '5432',
        'database': 'resume_customizer',
        'username': 'postgres',
        'password': 'Amit@8982'
    }
    
    # URL encode password to handle special characters
    password = quote_plus(config['password'])
    
    return (
        f"postgresql://{config['username']}:{password}@"
        f"{config['host']}:{config['port']}/{config['database']}"
    )