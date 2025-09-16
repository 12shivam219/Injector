# Neon PostgreSQL Deployment Guide

This guide explains how to deploy the application with Neon PostgreSQL, a serverless PostgreSQL service.

## Prerequisites

- A Neon PostgreSQL account (https://neon.tech)
- Your Neon connection string

## Configuration Steps

### 1. Environment Setup

Create or update your `.env` file with the following Neon-specific settings:

```
# Neon PostgreSQL Configuration
USE_NEON_DIRECT=true
NEON_CONNECTION_STRING=postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/dbname?sslmode=require

# Database Connection Pool Settings for Neon
DB_MIN_CONNECTIONS=2
DB_MAX_CONNECTIONS=10
DB_CONNECTION_TIMEOUT=30
DB_IDLE_TIMEOUT=300
DB_POOL_RECYCLE=300
```

### 2. Sharding Configuration

The application has been configured to support sharding with Neon PostgreSQL. When using Neon:

- The system will automatically create required shard databases if they don't exist
- Connection pooling is optimized for Neon's serverless architecture
- SSL is enforced for all connections

To configure the number of shards, set the following in your `.env` file:

```
DB_SHARD_COUNT=4  # Default is 4 shards
```

### 3. Testing the Connection

You can test your Neon connection by running:

```
python scripts/test_neon_connection.py
```

## Performance Considerations

### Connection Pooling

Neon PostgreSQL works best with these connection pool settings:

- Smaller initial pool size (2-3 connections)
- Moderate max connections (10-15)
- Shorter connection recycling time (300 seconds)
- Pre-ping enabled to verify connections

### Serverless Considerations

- Neon may have cold starts for inactive databases
- The first connection might take longer
- The application is configured to handle these characteristics automatically

## Troubleshooting

### Common Issues

1. **Connection Errors**: Ensure your Neon connection string is correct and includes `?sslmode=require`
2. **Database Creation Failures**: Verify your Neon user has permissions to create databases
3. **Slow Queries**: Initial connections may be slower due to Neon's serverless nature

### Logs to Check

- Database connection logs in the application output
- Neon's dashboard for query performance metrics

## Migration from Standard PostgreSQL

If migrating from a standard PostgreSQL deployment:

1. Export your data from the existing database
2. Import the data to your Neon database
3. Update your `.env` file with Neon settings
4. Restart the application

## Support

For Neon-specific issues, refer to the [Neon documentation](https://neon.tech/docs/).