"""Agencies above workspaces, and each person's place in one

Every existing workspace is put into an agency: workspaces that share a person become
one agency. Everyone in it becomes an Admin who can approve; a person who was a member
of every workspace in it reaches "all workspaces", anyone else keeps the workspaces
they had. `workspace_member` is left as it is: it stays the table access is read from.

Revision ID: 0048_agency
Revises: 0047_drop_eval_config_config
Create Date: 2026-11-23 20:00:00.000000

"""
import re
import uuid
from collections.abc import Iterable

import sqlalchemy as sa
import sqlmodel
from alembic import op


# revision identifiers, used by Alembic.
revision = '0048_agency'
down_revision = '0047_drop_eval_config_config'
branch_labels = None
depends_on = None


def name_from_email(email: str) -> str:
    """The rule that names a first workspace: the domain's first part, capitalised."""
    _, at, domain = email.rpartition("@")
    first = domain.strip().split(".")[0] if at else ""
    words = [w for w in re.split(r"[-_]", first) if w]
    name = " ".join(w[0].upper() + w[1:] for w in words)
    return name[:255] or "My workspace"


def group_into_agencies(
    workspaces: Iterable[tuple[str, str]],
    memberships: Iterable[tuple[str, str, str]],
) -> list[dict]:
    """Group workspaces that share a person.

    Args:
        workspaces: (workspace id, workspace name), every workspace.
        memberships: (user id, workspace id, user email), oldest membership first.

    Returns:
        One dict per agency: its `name`, its `workspaces`, and `members` as
        (user id, reaches every workspace of the agency).
    """
    names = dict(workspaces)
    parent = {w: w for w in names}

    def find(w: str) -> str:
        while parent[w] != w:
            parent[w] = parent[parent[w]]
            w = parent[w]
        return w

    first_of: dict[str, str] = {}
    reach: dict[str, set[str]] = {}
    email_of: dict[str, str] = {}
    order: list[str] = []
    for user, workspace, email in memberships:
        if workspace not in parent:
            continue
        if user not in reach:
            order.append(user)
        reach.setdefault(user, set()).add(workspace)
        email_of[user] = email
        if user in first_of:
            parent[find(workspace)] = find(first_of[user])
        else:
            first_of[user] = workspace

    groups: dict[str, list[str]] = {}
    for w in names:
        groups.setdefault(find(w), []).append(w)

    agencies = []
    for root, owned in groups.items():
        people = [u for u in order if find(first_of[u]) == root]
        agencies.append(
            {
                # Named from its oldest member's email; a workspace nobody is in
                # keeps its own name.
                "name": name_from_email(email_of[people[0]])
                if people
                else names[owned[0]],
                "workspaces": owned,
                "members": [(u, reach[u] == set(owned)) for u in people],
            }
        )
    return agencies


def upgrade() -> None:
    op.create_table(
        'agency',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'agency_member',
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'member', name='agencyrole', native_enum=False, length=32), nullable=False),
        sa.Column('all_workspaces', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('can_approve', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agency.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('agency_id', 'user_id'),
    )
    op.create_index(op.f('ix_agency_member_user_id'), 'agency_member', ['user_id'], unique=False)
    op.add_column('company', sa.Column('agency_id', sa.Uuid(), nullable=True))

    bind = op.get_bind()
    workspaces = [
        (str(row[0]), row[1])
        for row in bind.execute(sa.text('SELECT id, name FROM company ORDER BY created_at, id'))
    ]
    memberships = [
        (str(row[0]), str(row[1]), row[2])
        for row in bind.execute(
            sa.text(
                'SELECT m.user_id, m.company_id, u.email FROM workspace_member m '
                'JOIN "user" u ON u.id = m.user_id ORDER BY m.created_at, m.user_id, m.company_id'
            )
        )
    ]
    for agency in group_into_agencies(workspaces, memberships):
        agency_id = str(uuid.uuid4())
        bind.execute(
            sa.text('INSERT INTO agency (id, name) VALUES (:id, :name)'),
            {'id': agency_id, 'name': agency['name']},
        )
        for workspace_id in agency['workspaces']:
            bind.execute(
                sa.text('UPDATE company SET agency_id = :agency WHERE id = :id'),
                {'agency': agency_id, 'id': workspace_id},
            )
        for user_id, reaches_all in agency['members']:
            bind.execute(
                sa.text(
                    'INSERT INTO agency_member (agency_id, user_id, role, all_workspaces, can_approve) '
                    "VALUES (:agency, :user, 'admin', :all_workspaces, true)"
                ),
                {'agency': agency_id, 'user': user_id, 'all_workspaces': reaches_all},
            )

    op.alter_column('company', 'agency_id', nullable=False)
    op.create_index(op.f('ix_company_agency_id'), 'company', ['agency_id'], unique=False)
    op.create_foreign_key('company_agency_id_fkey', 'company', 'agency', ['agency_id'], ['id'])


def downgrade() -> None:
    # workspace_member was never changed, so access is as it was before the upgrade.
    op.drop_constraint('company_agency_id_fkey', 'company', type_='foreignkey')
    op.drop_index(op.f('ix_company_agency_id'), table_name='company')
    op.drop_column('company', 'agency_id')
    op.drop_index(op.f('ix_agency_member_user_id'), table_name='agency_member')
    op.drop_table('agency_member')
    op.drop_table('agency')
