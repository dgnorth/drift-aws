# Bits of info on running DB's in AWS

## Copying Postgres database between tiers

The following enviroment variables define the operation:

```bash
# Example arguments
export FROM_TIER=LIVENORTH
export TO_TIER=DEVNORTH
export DATABASE=dg-machinesar.drift-base

# These are inferred
export PGDATABASE=postgres
export PGUSER=postgres
export PGPASSWORD=postgres
```

### The backup operation:

The following commands must have access to the source DMBS and should preferably be executed in the same VPC as the DMBS.

```bash
# Dump operation
export PGHOST=postgres.${FROM_TIER}.dg-api.com
pg_dump -Fc ${DATABASE} > ${DATABASE}.pgdump
aws s3 cp ${DATABASE}.pgdump s3://dg-scratchpad/pgdumps/${DATABASE}.pgdump
rm ${DATABASE}.pgdump
```

Note, you can create a temporary download link to the pgdump file on S3 like this:

```bash
python -c "import boto3; print boto3.client('s3').generate_presigned_url('get_object', Params = {'Bucket': 'dg-scratchpad', 'Key': 'pgdumps/${DATABASE}.pgdump'}, ExpiresIn=3600)"
```

### The restore operation:
The following commands must have access to the destination DMBS and should preferably be executed in the same VPC as the DMBS. **Make sure the destination DB does not exist!**

```bash
# If the DB already exists, rename it or drop it!

# Rename database
psql -c "ALTER DATABASE \"${DATABASE}\" RENAME TO \"${DATABASE}.backup\""

# ..or drop database
psql -c "DROP DATABASE IF EXISTS \"${DATABASE}\""
```

Below is the actual restore operation. Note that it may take anywhere from minutes to hours to run.

```bash
# Restore operation.
export PGHOST=postgres.${TO_TIER}.dg-api.com
aws s3 cp s3://dg-scratchpad/pgdumps/${DATABASE}.pgdump .
pg_restore -Fc -C -d ${PGDATABASE} ${DATABASE}.pgdump

# Always clean up dumps because they might include sensitive data.
rm ${DATABASE}.pgdump
aws s3 rm s3://dg-scratchpad/pgdumps/${DATABASE}.pgdump
```
