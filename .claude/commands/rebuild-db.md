Rebuild the local database environment from scratch.

WARNING:
This operation may delete local environment data.

Steps:

1. Stop and remove existing containers, networks and volumes:
```bash
docker compose down -v
```

2. Rebuild and restart containers:
```bash
docker compose up --build -d
```

3. Apply Prisma migrations:
```bash
npx prisma migrate dev
```

4. Regenerate Prisma client:
```bash
npx prisma generate
```

5. Verify:
    - PostgreSQL is healthy
    - Redis responds correctly
    - Prisma migrations succeeded
    - Prisma client generated successfully

6. Summarize:
    - Containers rebuilt
    - Migration status
    - Any failures or warnings