<%!
import time
%>
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date or time.strftime("%Y-%m-%d %H:%M:%S")}
"""

from alembic import op
import sqlalchemy as sa

<% if imports: %>
${imports}
<% endif %>

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
<% if upgrades: %>
${upgrades}
<% else: %>
	pass
<% endif %>


def downgrade():
<% if downgrades: %>
${downgrades}
<% else: %>
	pass
<% endif %>
