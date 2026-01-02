"""
Database-safe C2 migration.

We use SeparateDatabaseAndState so Django's migration *state* knows about the fields/constraint,
while the database operations remain idempotent (IF NOT EXISTS) to survive branch switching.
"""

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("files", "0008_relax_pdffile_content_sha256"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
DO $$
BEGIN
    -- Add columns if they don't exist (handles DBs that already have them from prior experiments).
    BEGIN
        ALTER TABLE files_pdffile
            ADD COLUMN IF NOT EXISTS content_sha256 varchar(64);
    EXCEPTION WHEN undefined_table THEN
        NULL;
    END;

    BEGIN
        ALTER TABLE files_pdffile
            ADD COLUMN IF NOT EXISTS size_bytes bigint;
    EXCEPTION WHEN undefined_table THEN
        NULL;
    END;

    -- Ensure content_sha256 is nullable for compatibility (older rows/branches).
    BEGIN
        ALTER TABLE files_pdffile ALTER COLUMN content_sha256 DROP NOT NULL;
    EXCEPTION WHEN others THEN
        NULL;
    END;

    -- Add the per-user unique constraint if missing (only when sha present).
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uniq_user_content_sha256'
    ) THEN
        BEGIN
            ALTER TABLE files_pdffile
            ADD CONSTRAINT uniq_user_content_sha256
            UNIQUE (created_by_id, content_sha256)
            DEFERRABLE INITIALLY IMMEDIATE;
        EXCEPTION WHEN others THEN
            -- If something unexpected happens (e.g. column missing), don't brick migrations.
            NULL;
        END;
    END IF;
END $$;
""",
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="pdffile",
                    name="content_sha256",
                    field=models.CharField(
                        max_length=64, null=True, blank=True, db_index=True
                    ),
                ),
                migrations.AddField(
                    model_name="pdffile",
                    name="size_bytes",
                    field=models.BigIntegerField(null=True, blank=True),
                ),
                migrations.AddConstraint(
                    model_name="pdffile",
                    constraint=models.UniqueConstraint(
                        fields=("created_by", "content_sha256"),
                        condition=Q(content_sha256__isnull=False) & ~Q(
                            content_sha256=""
                        ),
                        name="uniq_user_content_sha256",
                    ),
                ),
            ],
        )
    ]


