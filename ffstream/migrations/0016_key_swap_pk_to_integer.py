"""
Migration: swap Key primary key from string (stream_key) to auto integer.

This migration requires a maintenance window on large databases due to:
- Full table update on ffstream_stream (may have millions of rows)
- Table lock during PK swap on ffstream_key

Steps:
1. Add _new_id SERIAL to ffstream_key
2. Add _new_key_id INTEGER NULL to ffstream_stream
3. Populate ffstream_stream._new_key_id via JOIN on old string key
4. Swap stream FK and key PK
"""
from django.db import migrations


FORWARD_SQL = [
    # Step 1: Add new integer sequence column to Key (not yet PK)
    "ALTER TABLE ffstream_key ADD COLUMN _new_id SERIAL",

    # Step 2: Add new integer FK column to Stream
    "ALTER TABLE ffstream_stream ADD COLUMN _new_key_id INTEGER",

    # Step 3: Populate Stream._new_key_id from Key._new_id via old string id
    """
    UPDATE ffstream_stream s
    SET _new_key_id = k._new_id
    FROM ffstream_key k
    WHERE s.key_id = k.id
    """,

    # Step 4: Make _new_key_id NOT NULL
    "ALTER TABLE ffstream_stream ALTER COLUMN _new_key_id SET NOT NULL",

    # Step 5: Drop old FK constraint from Stream
    "ALTER TABLE ffstream_stream DROP CONSTRAINT ffstream_stream_key_id_494c8e92_fk_ffstream_key_id",

    # Step 6: Drop old string key_id column from Stream
    "ALTER TABLE ffstream_stream DROP COLUMN key_id",

    # Step 7: Rename _new_key_id to key_id
    "ALTER TABLE ffstream_stream RENAME COLUMN _new_key_id TO key_id",

    # Step 8: Drop old string PK constraint from Key
    "ALTER TABLE ffstream_key DROP CONSTRAINT ffstream_key_pkey",

    # Step 9: Drop old string id column from Key
    "ALTER TABLE ffstream_key DROP COLUMN id",

    # Step 10: Rename _new_id to id
    "ALTER TABLE ffstream_key RENAME COLUMN _new_id TO id",

    # Step 11: Add PK constraint on new integer id
    "ALTER TABLE ffstream_key ADD PRIMARY KEY (id)",

    # Step 12: Add FK constraint from Stream.key_id to Key.id
    """
    ALTER TABLE ffstream_stream
    ADD CONSTRAINT ffstream_stream_key_id_fk_ffstream_key_id
    FOREIGN KEY (key_id) REFERENCES ffstream_key(id) DEFERRABLE INITIALLY DEFERRED
    """,

    # Step 13: Add index on Stream.key_id
    "CREATE INDEX ffstream_stream_key_id_idx ON ffstream_stream (key_id)",
]

REVERSE_SQL = [
    # Reversing this migration is not supported due to data complexity.
    # Restore from backup if rollback is needed.
]


class Migration(migrations.Migration):

    dependencies = [
        ('ffstream', '0015_key_stream_key_not_null_unique'),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
