from django.db import models, transaction, connection


class BordenNumberCounter(models.Model):
    """
    Tracks the current sequence number for each borden_grid prefix.

    Example borden_grid values: "DcRu", "DcRt", etc.
    The `grid_sequence` field stores the last allocated number.
    """

    borden_grid = models.CharField(max_length=4, primary_key=True)
    grid_sequence = models.BigIntegerField(default=0)

    class Meta:
        db_table = "bcap_borden_number_counters"
        verbose_name = "Borden Number Counter"
        verbose_name_plural = "Borden Number Counters"

    @classmethod
    def peek_next_borden_number(cls, borden_grid: str) -> str:
        """
        Returns what the next Borden number *would be* for a given borden_grid
        without updating the counter.

        If the borden_grid has not yet been initialized, assumes grid_sequence = 0.
        """
        with connection.cursor() as cur:
            cur.execute(
                "SELECT grid_sequence FROM bcap_borden_number_counters WHERE borden_grid = %s",
                [borden_grid],
            )
            row = cur.fetchone()
            next_grid_sequence = (row[0] if row else 0) + 1

        return f"{borden_grid}-{next_grid_sequence}"

    @classmethod
    @transaction.atomic
    def allocate_next_borden_number(cls, borden_grid: str) -> str:
        """
        Atomically increments and returns the next Borden number for the given borden_grid.
        Ensures no duplicates even across concurrent requests.
        """
        with connection.cursor() as cur:
            # Ensure row exists
            cur.execute(
                """
                INSERT INTO bcap_borden_number_counters(borden_grid, grid_sequence)
                VALUES (%s, 0)
                ON CONFLICT (borden_grid) DO NOTHING
                """,
                [borden_grid],
            )

            # Atomically increment and return new grid_sequence
            cur.execute(
                """
                UPDATE bcap_borden_number_counters
                   SET grid_sequence = grid_sequence + 1
                 WHERE borden_grid = %s
             RETURNING grid_sequence
                """,
                [borden_grid],
            )
            seq = cur.fetchone()[0]

        return f"{borden_grid}-{seq}"

    def __str__(self):
        return f"{self.borden_grid}: {self.grid_sequence}"
