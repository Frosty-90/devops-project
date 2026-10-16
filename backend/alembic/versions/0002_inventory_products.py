"""Replace the starter tasks table with the inventory products table."""
from alembic import op
import sqlalchemy as sa

revision = "0002_inventory_products"
down_revision = "0001_create_tasks"
branch_labels = None
depends_on = None

def upgrade():
    op.drop_table("tasks")
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(length=40), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="General"),
        sa.Column("supplier", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_level", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_products_quantity_non_negative"),
    )

def downgrade():
    op.drop_table("products")
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="TODO"),
        sa.Column("assignee", sa.String(length=120), nullable=False, server_default="Unassigned"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
