# Changelog

## [0.3.0]

_24 Aug 2026_

### Changed:

- Update document retrieval to align with ETSI TS 119 432 v1.3.1.

## [0.2.0]

_28 May 2025_

### Added:

- Docker support for the application:
  - Added Dockerfile to build the application image.
  - Added docker-compose.yml.
  - Instructions for building and running the container added to README.md.

## [0.1.0]

_13 Jan 2025_

### Added:

- Initial release of the Relying Party Web Service.
- Support for form-based login.
- Ability to request a document signature from the EUDI Wallet:
  - Support for the following 'client_id_schemes': 'x509_san_dns', 'pre-registered'
- Example document provided for testing signatures.
