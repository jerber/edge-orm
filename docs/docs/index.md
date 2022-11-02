# EdgeORM

*Simple, powerful, and fully typed Python ORM for working with graph-relational databases.*

### Query

```Python
from app.dbs import db

user = await db.UserResolver().friends().limit(10).get(id='123')
for user in users:
    names_of_friends = ", ".join([f.name for f in await user.friends()])
    print(f'{user.name} is friends with {names_of_friends}')

```


# Welcome to MkDocs

For full documentation visit [mkdocs.org](https://www.mkdocs.org).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.
