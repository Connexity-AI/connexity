
// Starter projects

// map next.js to fastapi, redirect `next.config.js`, useless, no database. hello world route
https://github.com/digitros/nextjs-fastapi
------
// simple, minimal, sqlmodel orm
https://github.com/testdrivenio/fastapi-sqlmodel-alembic
-------
// fastapi backend only
//  excellent fastapi, rocketry as scheduler, rabbitmq
zesce nekompletan, samo redis i db u docker, fastapi u venv, bezveze
ima greske u readme, .env, d-c.dev.yml, nema app i docs url...
https://github.com/kamranabdicse/fastapi-postgres-boilerplate
----------
// another, better, redis broker, terraform
https://github.com/jonra1993/fastapi-alembic-sqlmodel-async
// kazakhstan, maybe this, SAMO redis, nema rabbitmq i celery, not single db model
https://github.com/zhanymkanov/fastapi_production_template
------
// losi
// solidan, mali, fastapi, hackernews kandidat
https://github.com/innovatorved/whisper.api
// docs, los outdated
// https://github.com/tiangolo/full-stack-fastapi-postgresql
-----
// dobar, linkedin, jedini ima rabbitmq broker
https://github.com/AdrianPayne/fastapi-rocket-boilerplate
// promenio github username, sad je:
https://github.com/asacristani/fastapi-rocket-boilerplate
pulumi kao python lib u __main__.py
crud je u app/core/models/base.py
------
// generator, redis, rabbitmq, logging
// bezveze orms, cookiecutter mnogo, neupotrebljiv, jedino redovi
https://github.com/s3rius/FastAPI-template
-----
// two similar with arq
// another from linkedin
https://github.com/igormagalhaesr/FastAPI-boilerplate
// renamed to:
https://github.com/benavlabs/FastAPI-boilerplate
// sve preuzeto iz tiangolo
kopira samo app folder u Dockerfile, ne postavlja PYTHONPATH
COPY ./src/app /code/app
----
models - tip za bazu
schemas - tipovi pydantic
poziva samo sa gen tipovima, nema args
CRUDUser = CRUDBase[User, UserInDB, UserUpdateDB]
------
https://github.dev/benavlabs/SQLModel-boilerplate
fastcrud package - najveca mana
kompletan primer, auth, testovi, kvalitetna struktura
poetry
-------
// dobar zapravo, kubernetes
https://github.com/Kludex/fastapi-microservices
Tiltfile - maps Dockerfile to kubernetes
