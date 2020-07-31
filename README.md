# zorya
A microservice to package bags.

zorya is part of [Project Electron](https://github.com/RockefellerArchiveCenter/project_electron), an initiative to build sustainable, open and user-centered infrastructure for the archival management of digital records at the [Rockefeller Archive Center](http://rockarch.org/).

## Setup

Install [git](https://git-scm.com/) and clone the repository

    $ git clone https://github.com/RockefellerArchiveCenter/zorya.git

Install [Docker](https://store.docker.com/search?type=edition&offering=community) and run docker-compose from the root directory

    $ cd zorya
    $ docker-compose up

Once the application starts successfully, you should be able to access the application in your browser at `http://localhost:8005`

When you're done, shut down docker-compose

    $ docker-compose down

Or, if you want to remove all data

    $ docker-compose down -v

## Services

* Validate and rename bag
* Get rights information from external service
* Create delivery package
* Send delivery package to an external application

### Routes


| Method | URL | Parameters | Response  | Behavior  |
|--------|-----|---|---|---|
|GET|/bags| |200|Returns a list of bags|
|GET|/bags/{id}| |200|Returns data about an individual bag|
|POST|/discover-bags| |200|Discovers bags waiting to be processed|
|POST|/assign-rights| |200|Fetches rights information from external service|
|POST|/make-package| |200|Assembles a package to be delivered to an external service|
|POST|/deliver-package| |200|Delivers package to an external service|


## Requirements

Using this repo requires having [Docker](https://store.docker.com/search?type=edition&offering=community) installed.

## License

Code is released under an MIT License, as all your code should be. See [LICENSE](LICENSE) for details.
