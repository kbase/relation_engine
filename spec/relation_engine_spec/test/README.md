# Relation Engine Spec Tests

This directory holds python unit-tests for Relation Engine views and migrations.

A view test should test that a query returns the expected data, traverses the graph correctly, and
does not return data that we don't want.

A migration test should test that all the data in a test database has been updated in the correct
way after a migration is run. It should also test that when a migration rolls back, data is
restored to its original form.
