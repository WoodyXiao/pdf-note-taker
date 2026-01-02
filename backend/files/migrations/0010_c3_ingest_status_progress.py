"""
Database-safe C3 migration.

SeparateDatabaseAndState keeps Django migration state aligned with the model fields,
while database operations remain idempotent to survive branch switching.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("files", "0009_c2_pdffile_dedup_fields"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
DO $$
BEGIN
    -- Add columns (safe if they already exist).
    ALTER TABLE files_pdffile
        ADD COLUMN IF NOT EXISTS ingest_status varchar(16) DEFAULT 'pending';
    ALTER TABLE files_pdffile
        ADD COLUMN IF NOT EXISTS ingest_progress smallint DEFAULT 0;
    ALTER TABLE files_pdffile
        ADD COLUMN IF NOT EXISTS ingest_total_chunks integer;
    ALTER TABLE files_pdffile
        ADD COLUMN IF NOT EXISTS ingest_done_chunks integer;
    ALTER TABLE files_pdffile
        ADD COLUMN IF NOT EXISTS ingest_started_at timestamptz;
    ALTER TABLE files_pdffile
        ADD COLUMN IF NOT EXISTS ingest_finished_at timestamptz;

    -- Backfill from existing boolean/error fields.
    -- is_ingested=false => running (or pending). We treat as running because UI previously showed "Processing".
    UPDATE files_pdffile
      SET ingest_status = 'running',
          ingest_progress = COALESCE(ingest_progress, 0)
    WHERE is_ingested = false
      AND (ingest_status IS NULL OR ingest_status = 'pending');

    -- is_ingested=true and no error => succeeded
    UPDATE files_pdffile
      SET ingest_status = 'succeeded',
          ingest_progress = 100
    WHERE is_ingested = true
      AND (ingest_error IS NULL OR ingest_error = '')
      AND (ingest_status IS NULL OR ingest_status IN ('pending','running'));

    -- is_ingested=true and has error => failed
    UPDATE files_pdffile
      SET ingest_status = 'failed',
          ingest_progress = 100
    WHERE is_ingested = true
      AND (ingest_error IS NOT NULL AND ingest_error <> '')
      AND (ingest_status IS NULL OR ingest_status IN ('pending','running'));
END $$;
""",
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="pdffile",
                    name="ingest_status",
                    field=models.CharField(
                        max_length=16,
                        default="pending",
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                    ),
                ),
                migrations.AddField(
                    model_name="pdffile",
                    name="ingest_progress",
                    field=models.PositiveSmallIntegerField(default=0),
                ),
                migrations.AddField(
                    model_name="pdffile",
                    name="ingest_total_chunks",
                    field=models.IntegerField(null=True, blank=True),
                ),
                migrations.AddField(
                    model_name="pdffile",
                    name="ingest_done_chunks",
                    field=models.IntegerField(null=True, blank=True),
                ),
                migrations.AddField(
                    model_name="pdffile",
                    name="ingest_started_at",
                    field=models.DateTimeField(null=True, blank=True),
                ),
                migrations.AddField(
                    model_name="pdffile",
                    name="ingest_finished_at",
                    field=models.DateTimeField(null=True, blank=True),
                ),
            ],
        )
    ]


