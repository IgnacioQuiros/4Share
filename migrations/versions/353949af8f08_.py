"""empty message

Revision ID: 353949af8f08
Revises: 
Create Date: 2024-09-20 18:51:40.152093

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '353949af8f08'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password', sa.String(length=80), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('name', sa.String(length=30), nullable=True),
    sa.Column('last_name', sa.String(length=30), nullable=True),
    sa.Column('location', sa.String(length=50), nullable=True),
    sa.Column('language', sa.String(length=70), nullable=True),
    sa.Column('gender', sa.String(length=50), nullable=True),
    sa.Column('profile_pic', sa.String(length=255), nullable=True),
    sa.Column('description', sa.String(length=250), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('best_sharers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('media_average', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('skill_name', postgresql.ENUM('Cooking', 'Sports', 'Music', 'Languages', 'Art', 'Others', name='skill_name_enum'), nullable=False),
    sa.Column('description', sa.String(length=250), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'skill_name', name='unique_user_skill')
    )
    op.create_table('favorite',
    sa.Column('favorite_id', sa.Integer(), nullable=False),
    sa.Column('favorite_from_id', sa.Integer(), nullable=False),
    sa.Column('favorite_to_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['favorite_from_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['favorite_to_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('favorite_id')
    )
    op.create_table('matches',
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('match_from_id', sa.Integer(), nullable=False),
    sa.Column('match_to_id', sa.Integer(), nullable=False),
    sa.Column('match_status', postgresql.ENUM('Pending', 'Accepted', 'Rejected', 'Ignored', name='match_status_enum'), nullable=False),
    sa.ForeignKeyConstraint(['match_from_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['match_to_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('match_id')
    )
    op.create_table('reviews',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('reviewer_id', sa.Integer(), nullable=False),
    sa.Column('reviewee_id', sa.Integer(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('comment', sa.String(length=250), nullable=True),
    sa.ForeignKeyConstraint(['reviewee_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['reviewer_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('token_restore_password',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('reset_token', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('reset_token')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('token_restore_password')
    op.drop_table('reviews')
    op.drop_table('matches')
    op.drop_table('favorite')
    op.drop_table('categories')
    op.drop_table('best_sharers')
    op.drop_table('user')
    # ### end Alembic commands ###
