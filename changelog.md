# Changelog

## [0.3.1]

_9 Oct 2026_

### Changed:

- Updated document retrieval request object (JAR) `typ` header to `oauth-authz-req+jwt`, as expected by OpenID4VP.
- Updated document retrieval `signed_envelope_property` and `conformance_level` values to align with the CSC Data Model v1.0.0.

## [0.3.0]

_2 Oct 2026_

### Added:

- Added support for ITB tests, including endpoints for QR code generation, logs retrieval, and signed document upload.

### Changed:

- Updated document retrieval to align with ETSI TS 119 432 v1.3.1.
- Refactoring code, including cleanup and bug fixes.

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
