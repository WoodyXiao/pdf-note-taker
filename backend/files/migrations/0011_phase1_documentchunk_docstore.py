"""
Phase 1 (video-style RAG): add DocumentChunk doc store and link DocumentEmbedding -> DocumentChunk.

We use SeparateDatabaseAndState to keep migrations resilient across branch switching:
- DB operations are idempotent (IF NOT EXISTS)
- State operations tell Django about the model/field so it won't auto-generate duplicates.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("files", "0010_c3_ingest_status_progress"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
DO $$
BEGIN
    -- Create doc store table if missing.
    CREATE TABLE IF NOT EXISTS files_documentchunk (
        id uuid PRIMARY KEY,
        chunk_type varchar(16) NOT NULL DEFAULT 'text',
        title varchar(255) NOT NULL DEFAULT '',
        page_start integer NULL,
        page_end integer NULL,
        raw_text text NOT NULL DEFAULT '',
        metadata jsonb NULL,
        created_at timestamptz NOT NULL DEFAULT NOW(),
        file_id bigint NOT NULL
    );

    -- Ensure FK to PdfFile exists.
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'files_documentchunk_file_fk'
    ) THEN
        BEGIN
            ALTER TABLE files_documentchunk
            ADD CONSTRAINT files_documentchunk_file_fk
            FOREIGN KEY (file_id) REFERENCES files_pdffile(id)
            ON DELETE CASCADE;
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;

    -- Add embedding -> chunk link if missing.
    BEGIN
        ALTER TABLE files_documentembedding
            ADD COLUMN IF NOT EXISTS chunk_id uuid;
    EXCEPTION WHEN undefined_table THEN
        NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'files_docembed_chunk_fk'
    ) THEN
        BEGIN
            ALTER TABLE files_documentembedding
            ADD CONSTRAINT files_docembed_chunk_fk
            FOREIGN KEY (chunk_id) REFERENCES files_documentchunk(id)
            ON DELETE CASCADE;
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;

    -- Helpful index for joins.
    CREATE INDEX IF NOT EXISTS files_documentembedding_chunk_id_idx
        ON files_documentembedding(chunk_id);
END $$;
""",
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[
                migrations.CreateModel(
                    name="DocumentChunk",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                primary_key=True,
                                editable=False,
                                serialize=False,
                            ),
                        ),
                        (
                            "chunk_type",
                            models.CharField(
                                choices=[
                                    ("text", "Text"),
                                    ("table", "Table"),
                                    ("image", "Image"),
                                ],
                                default="text",
                                max_length=16,
                            ),
                        ),
                        ("title", models.CharField(blank=True, max_length=255)),
                        ("page_start", models.IntegerField(blank=True, null=True)),
                        ("page_end", models.IntegerField(blank=True, null=True)),
                        ("raw_text", models.TextField(blank=True)),
                        ("metadata", models.JSONField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "file",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="chunks",
                                to="files.pdffile",
                            ),
                        ),
                    ],
                    options={"ordering": ["created_at"]},
                ),
                migrations.AddField(
                    model_name="documentembedding",
                    name="chunk",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embeddings",
                        to="files.documentchunk",
                    ),
                ),
            ],
        )
    ]


