"""Initial migration - Create all tables

Revision ID: 001
Revises:
Create Date: 2024-10-20 19:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create agents table
    op.create_table('agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary key identifier', default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Agent display name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Agent description'),
        sa.Column('agent_type', sa.String(length=50), nullable=False, comment='Type of agent'),
        sa.Column('version', sa.String(length=50), nullable=False, comment='Agent version'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Current agent status'),
        sa.Column('health_status', sa.String(length=50), nullable=False, comment='Agent health status'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether agent is active'),
        sa.Column('is_public', sa.Boolean(), nullable=False, comment='Whether agent is publicly accessible'),
        sa.Column('config', sa.JSON(), nullable=True, comment='Agent configuration'),
        sa.Column('capabilities', postgresql.ARRAY(sa.String()), nullable=True, comment='Agent capabilities'),
        sa.Column('tools', sa.JSON(), nullable=True, comment='Assigned tools configuration'),
        sa.Column('constraints', sa.JSON(), nullable=True, comment='Agent constraints and limits'),
        sa.Column('endpoint_url', sa.String(length=500), nullable=True, comment='Agent endpoint URL'),
        sa.Column('api_key', sa.String(length=255), nullable=True, comment='API key for external access'),
        sa.Column('max_concurrent_tasks', sa.Integer(), nullable=False, comment='Maximum concurrent tasks'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, comment='Task timeout in seconds'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True, comment='Last heartbeat timestamp'),
        sa.Column('response_time_avg', sa.Float(), nullable=True, comment='Average response time in milliseconds'),
        sa.Column('success_rate', sa.Float(), nullable=True, comment='Success rate as percentage (0-100)'),
        sa.Column('total_tasks', sa.Integer(), nullable=False, comment='Total tasks processed'),
        sa.Column('failed_tasks', sa.Integer(), nullable=False, comment='Total failed tasks'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='User who created the agent'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, comment='Agent tags for categorization'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Soft delete timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("agent_type IN ('chat', 'workflow', 'task', 'monitoring', 'coordinator', 'specialized')", name='check_agent_type'),
        sa.CheckConstraint("status IN ('pending', 'active', 'idle', 'busy', 'error', 'maintenance', 'decommissioned')", name='check_agent_status'),
        sa.CheckConstraint("health_status IN ('healthy', 'degraded', 'unhealthy', 'unknown')", name='check_health_status'),
        sa.CheckConstraint('max_concurrent_tasks > 0', name='check_max_concurrent_tasks_positive'),
        sa.CheckConstraint('timeout_seconds > 0', name='check_timeout_positive'),
        sa.CheckConstraint('success_rate >= 0 AND success_rate <= 100', name='check_success_rate_range'),
        sa.CheckConstraint('total_tasks >= 0', name='check_total_tasks_non_negative'),
        sa.CheckConstraint('failed_tasks >= 0', name='check_failed_tasks_non_negative'),
        comment='Agent model representing an AI agent with capabilities and lifecycle management.'
    )
    op.create_index('idx_agents_status_active', 'agents', ['status', 'is_active'], unique=False)
    op.create_index('idx_agents_type_status', 'agents', ['agent_type', 'status'], unique=False)
    op.create_index('idx_agents_created_by', 'agents', ['created_by'], unique=False)
    op.create_index('idx_agents_last_heartbeat', 'agents', ['last_heartbeat'], unique=False)
    op.create_index(op.f('ix_agents_name'), 'agents', ['name'], unique=False)

    # Create workflows table
    op.create_table('workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary key identifier', default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Workflow display name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Workflow description'),
        sa.Column('version', sa.String(length=50), nullable=False, comment='Workflow version'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Current workflow status'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether workflow is active'),
        sa.Column('is_template', sa.Boolean(), nullable=False, comment='Whether this is a template workflow'),
        sa.Column('definition', sa.JSON(), nullable=True, comment='Workflow definition JSON'),
        sa.Column('config', sa.JSON(), nullable=True, comment='Workflow configuration'),
        sa.Column('variables', sa.JSON(), nullable=True, comment='Workflow variables schema'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, comment='Workflow timeout in seconds'),
        sa.Column('max_retries', sa.Integer(), nullable=False, comment='Maximum retry attempts'),
        sa.Column('total_executions', sa.Integer(), nullable=False, comment='Total number of executions'),
        sa.Column('successful_executions', sa.Integer(), nullable=False, comment='Number of successful executions'),
        sa.Column('failed_executions', sa.Integer(), nullable=False, comment='Number of failed executions'),
        sa.Column('last_execution_at', sa.DateTime(timezone=True), nullable=True, comment='Last execution timestamp'),
        sa.Column('average_execution_time', sa.Float(), nullable=True, comment='Average execution time in seconds'),
        sa.Column('template_category', sa.String(length=100), nullable=True, comment='Template category'),
        sa.Column('template_tags', postgresql.ARRAY(sa.String()), nullable=True, comment='Template tags'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='User who created the workflow'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, comment='Workflow tags for categorization'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Soft delete timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('draft', 'active', 'paused', 'completed', 'failed', 'cancelled', 'archived')", name='check_workflow_status'),
        sa.CheckConstraint('max_retries >= 0', name='check_max_retries_non_negative'),
        sa.CheckConstraint('timeout_seconds IS NULL OR timeout_seconds > 0', name='check_timeout_positive'),
        sa.CheckConstraint('total_executions >= 0', name='check_total_executions_non_negative'),
        sa.CheckConstraint('successful_executions >= 0', name='check_successful_executions_non_negative'),
        sa.CheckConstraint('failed_executions >= 0', name='check_failed_executions_non_negative'),
        comment='Workflow model representing a complex workflow with DAG-based execution.'
    )
    op.create_index('idx_workflows_status_active', 'workflows', ['status', 'is_active'], unique=False)
    op.create_index('idx_workflows_template', 'workflows', ['is_template', 'template_category'], unique=False)
    op.create_index('idx_workflows_created_by', 'workflows', ['created_by'], unique=False)
    op.create_index('idx_workflows_last_execution', 'workflows', ['last_execution_at'], unique=False)
    op.create_index(op.f('ix_workflows_name'), 'workflows', ['name'], unique=False)

    # Create tools table
    op.create_table('tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary key identifier', default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Tool display name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Tool description'),
        sa.Column('tool_type', sa.String(length=50), nullable=False, comment='Type of tool'),
        sa.Column('category', sa.String(length=50), nullable=True, comment='Tool category'),
        sa.Column('version', sa.String(length=50), nullable=False, comment='Tool version'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Current tool status'),
        sa.Column('is_public', sa.Boolean(), nullable=False, comment='Whether tool is publicly accessible'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, comment='Whether tool is verified'),
        sa.Column('config', sa.JSON(), nullable=True, comment='Tool configuration'),
        sa.Column('parameters_schema', sa.JSON(), nullable=True, comment='JSON schema for parameters'),
        sa.Column('input_schema', sa.JSON(), nullable=True, comment='Expected input schema'),
        sa.Column('output_schema', sa.JSON(), nullable=True, comment='Expected output schema'),
        sa.Column('examples', sa.JSON(), nullable=True, comment='Usage examples'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, comment='Default timeout in seconds'),
        sa.Column('max_retries', sa.Integer(), nullable=False, comment='Maximum retry attempts'),
        sa.Column('requires_auth', sa.Boolean(), nullable=False, comment='Whether tool requires authentication'),
        sa.Column('auth_config', sa.JSON(), nullable=True, comment='Authentication configuration'),
        sa.Column('endpoint_url', sa.String(length=500), nullable=True, comment='External tool endpoint URL'),
        sa.Column('webhook_url', sa.String(length=500), nullable=True, comment='Webhook URL for callbacks'),
        sa.Column('api_key_required', sa.Boolean(), nullable=False, comment='Whether API key is required'),
        sa.Column('memory_mb', sa.Integer(), nullable=True, comment='Memory requirement in MB'),
        sa.Column('cpu_cores', sa.Float(), nullable=True, comment='CPU cores requirement'),
        sa.Column('max_file_size_mb', sa.Integer(), nullable=True, comment='Maximum file size in MB'),
        sa.Column('usage_count', sa.Integer(), nullable=False, comment='Total usage count'),
        sa.Column('success_count', sa.Integer(), nullable=False, comment='Successful usage count'),
        sa.Column('error_count', sa.Integer(), nullable=False, comment='Error usage count'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True, comment='Last usage timestamp'),
        sa.Column('average_execution_time', sa.Float(), nullable=True, comment='Average execution time in seconds'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='User who created the tool'),
        sa.Column('documentation_url', sa.String(length=500), nullable=True, comment='Documentation URL'),
        sa.Column('repository_url', sa.String(length=500), nullable=True, comment='Source repository URL'),
        sa.Column('license', sa.String(length=100), nullable=True, comment='Tool license'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, comment='Tool tags for categorization'),
        sa.Column('dependencies', sa.JSON(), nullable=True, comment='Tool dependencies'),
        sa.Column('system_requirements', sa.JSON(), nullable=True, comment='System requirements'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Soft delete timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("tool_type IN ('builtin', 'custom', 'external_api', 'script', 'webhook', 'database', 'file_operation', 'ai_model')", name='check_tool_type'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'deprecated', 'error', 'testing')", name='check_tool_status'),
        sa.CheckConstraint('max_retries >= 0', name='check_tool_max_retries_non_negative'),
        sa.CheckConstraint('timeout_seconds IS NULL OR timeout_seconds > 0', name='check_tool_timeout_positive'),
        sa.CheckConstraint('usage_count >= 0', name='check_usage_count_non_negative'),
        sa.CheckConstraint('success_count >= 0', name='check_success_count_non_negative'),
        sa.CheckConstraint('error_count >= 0', name='check_error_count_non_negative'),
        sa.CheckConstraint('memory_mb IS NULL OR memory_mb > 0', name='check_memory_positive'),
        sa.CheckConstraint('cpu_cores IS NULL OR cpu_cores > 0', name='check_cpu_cores_positive'),
        sa.UniqueConstraint('name', 'deleted_at', name='idx_tools_name_unique'),
        comment='Tool model representing a tool that can be used by agents.'
    )
    op.create_index('idx_tools_status_active', 'tools', ['status', 'is_public'], unique=False)
    op.create_index('idx_tools_type_category', 'tools', ['tool_type', 'category'], unique=False)
    op.create_index('idx_tools_created_by', 'tools', ['created_by'], unique=False)
    op.create_index('idx_tools_last_used', 'tools', ['last_used_at'], unique=False)
    op.create_index(op.f('ix_tools_name'), 'tools', ['name'], unique=False)

    # Create workflow_nodes table
    op.create_table('workflow_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary key identifier', default=sa.text('gen_random_uuid()')),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Parent workflow ID'),
        sa.Column('node_id', sa.String(length=255), nullable=False, comment='Node identifier within workflow'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='Node display name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Node description'),
        sa.Column('node_type', sa.String(length=50), nullable=False, comment='Node type'),
        sa.Column('config', sa.JSON(), nullable=True, comment='Node configuration'),
        sa.Column('input_schema', sa.JSON(), nullable=True, comment='Expected input schema'),
        sa.Column('output_schema', sa.JSON(), nullable=True, comment='Expected output schema'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, comment='Node timeout in seconds'),
        sa.Column('retry_count', sa.Integer(), nullable=False, comment='Number of retry attempts'),
        sa.Column('max_retries', sa.Integer(), nullable=False, comment='Maximum retry attempts'),
        sa.Column('position_x', sa.Float(), nullable=True, comment='X position in workflow diagram'),
        sa.Column('position_y', sa.Float(), nullable=True, comment='Y position in workflow diagram'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("node_type IN ('trigger', 'agent_task', 'decision', 'parallel', 'sink', 'delay', 'webhook', 'script')", name='check_node_type'),
        sa.CheckConstraint('max_retries >= 0', name='check_node_max_retries_non_negative'),
        sa.CheckConstraint('retry_count >= 0', name='check_node_retry_count_non_negative'),
        sa.CheckConstraint('timeout_seconds IS NULL OR timeout_seconds > 0', name='check_node_timeout_positive'),
        sa.UniqueConstraint('workflow_id', 'node_id', name='idx_workflow_nodes_unique'),
        comment='Workflow node model representing individual workflow steps.'
    )
    op.create_index('idx_workflow_nodes_workflow_id', 'workflow_nodes', ['workflow_id'], unique=False)
    op.create_index('idx_workflow_nodes_type', 'workflow_nodes', ['node_type'], unique=False)
    op.create_index(op.f('ix_workflow_nodes_name'), 'workflow_nodes', ['name'], unique=False)

    # Create workflow_executions table
    op.create_table('workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary key identifier', default=sa.text('gen_random_uuid()')),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Parent workflow ID'),
        sa.Column('execution_id', sa.String(length=255), nullable=False, comment='Unique execution identifier'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Current execution status'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='Execution start timestamp'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='Execution completion timestamp'),
        sa.Column('duration_seconds', sa.Float(), nullable=True, comment='Total execution duration in seconds'),
        sa.Column('input_data', sa.JSON(), nullable=True, comment='Input data for execution'),
        sa.Column('output_data', sa.JSON(), nullable=True, comment='Output data from execution'),
        sa.Column('variables', sa.JSON(), nullable=True, comment='Execution variables'),
        sa.Column('context', sa.JSON(), nullable=True, comment='Execution context'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if failed'),
        sa.Column('error_details', sa.JSON(), nullable=True, comment='Detailed error information'),
        sa.Column('checkpoint_data', sa.JSON(), nullable=True, comment='Checkpoint data for recovery'),
        sa.Column('last_checkpoint_at', sa.DateTime(timezone=True), nullable=True, comment='Last checkpoint timestamp'),
        sa.Column('triggered_by', sa.String(length=100), nullable=True, comment='What triggered this execution'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')", name='check_execution_status'),
        sa.CheckConstraint('duration_seconds IS NULL OR duration_seconds >= 0', name='check_duration_non_negative'),
        sa.UniqueConstraint('workflow_id', 'execution_id', name='idx_workflow_executions_unique'),
        comment='Workflow execution model tracking individual workflow runs.'
    )
    op.create_index('idx_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'], unique=False)
    op.create_index('idx_workflow_executions_status', 'workflow_executions', ['status'], unique=False)
    op.create_index('idx_workflow_executions_started', 'workflow_executions', ['started_at'], unique=False)
    op.create_index(op.f('ix_workflow_executions_execution_id'), 'workflow_executions', ['execution_id'], unique=False)

    # Create execution_snapshots table
    op.create_table('execution_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary key identifier', default=sa.text('gen_random_uuid()')),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Workflow execution ID'),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Workflow ID'),
        sa.Column('snapshot_id', sa.String(length=255), nullable=False, comment='Unique snapshot identifier'),
        sa.Column('snapshot_type', sa.String(length=50), nullable=False, comment='Type of snapshot'),
        sa.Column('snapshot_level', sa.String(length=50), nullable=False, comment='Detail level of snapshot'),
        sa.Column('node_id', sa.String(length=255), nullable=True, comment='Node ID if snapshot is for a specific node'),
        sa.Column('node_type', sa.String(length=50), nullable=True, comment='Node type if applicable'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Execution status at snapshot time'),
        sa.Column('state_data', sa.JSON(), nullable=True, comment='Complete state data'),
        sa.Column('variables', sa.JSON(), nullable=True, comment='Workflow variables at snapshot time'),
        sa.Column('context', sa.JSON(), nullable=True, comment='Execution context'),
        sa.Column('input_data', sa.JSON(), nullable=True, comment='Node input data'),
        sa.Column('output_data', sa.JSON(), nullable=True, comment='Node output data'),
        sa.Column('node_config', sa.JSON(), nullable=True, comment='Node configuration at snapshot time'),
        sa.Column('execution_time_seconds', sa.Float(), nullable=True, comment='Execution time at snapshot point'),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True, comment='Memory usage in MB at snapshot time'),
        sa.Column('cpu_usage_percent', sa.Float(), nullable=True, comment='CPU usage percentage at snapshot time'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if any'),
        sa.Column('error_details', sa.JSON(), nullable=True, comment='Detailed error information'),
        sa.Column('stack_trace', sa.Text(), nullable=True, comment='Error stack trace'),
        sa.Column('is_checkpoint', sa.Boolean(), nullable=False, comment='Whether this is a recovery checkpoint'),
        sa.Column('checkpoint_data', sa.JSON(), nullable=True, comment='Checkpoint recovery data'),
        sa.Column('recovery_point', sa.String(length=255), nullable=True, comment='Recovery point identifier'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Snapshot creation timestamp'),
        sa.Column('created_by', sa.String(length=100), nullable=True, comment='What created this snapshot'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='Snapshot tags'),
        sa.Column('description', sa.Text(), nullable=True, comment='Snapshot description'),
        sa.Column('data_size_bytes', sa.Integer(), nullable=False, comment='Size of snapshot data in bytes'),
        sa.Column('is_compressed', sa.Boolean(), nullable=False, comment='Whether snapshot data is compressed'),
        sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("snapshot_type IN ('node_start', 'node_complete', 'node_error', 'workflow_start', 'workflow_complete', 'workflow_error', 'checkpoint', 'user_action', 'system_event')", name='check_snapshot_type'),
        sa.CheckConstraint("snapshot_level IN ('minimal', 'basic', 'detailed', 'full')", name='check_snapshot_level'),
        sa.CheckConstraint('execution_time_seconds IS NULL OR execution_time_seconds >= 0', name='check_execution_time_non_negative'),
        sa.CheckConstraint('memory_usage_mb IS NULL OR memory_usage_mb >= 0', name='check_memory_usage_non_negative'),
        sa.CheckConstraint('cpu_usage_percent IS NULL OR (cpu_usage_percent >= 0 AND cpu_usage_percent <= 100)', name='check_cpu_usage_range'),
        sa.CheckConstraint('data_size_bytes >= 0', name='check_data_size_non_negative'),
        sa.UniqueConstraint('execution_id', 'snapshot_id', name='idx_execution_snapshots_unique'),
        comment='Execution snapshot model capturing workflow execution state.'
    )
    op.create_index('idx_execution_snapshots_execution_id', 'execution_snapshots', ['execution_id'], unique=False)
    op.create_index('idx_execution_snapshots_workflow_id', 'execution_snapshots', ['workflow_id'], unique=False)
    op.create_index('idx_execution_snapshots_type', 'execution_snapshots', ['snapshot_type'], unique=False)
    op.create_index('idx_execution_snapshots_node', 'execution_snapshots', ['node_id'], unique=False)
    op.create_index('idx_execution_snapshots_created', 'execution_snapshots', ['created_at'], unique=False)
    op.create_index('idx_execution_snapshots_checkpoint', 'execution_snapshots', ['is_checkpoint'], unique=False)
    op.create_index(op.f('ix_execution_snapshots_snapshot_id'), 'execution_snapshots', ['snapshot_id'], unique=False)

    # Create agent_tools table (many-to-many relationship)
    op.create_table('agent_tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Primary key identifier', default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Agent ID'),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Tool ID'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Assignment status'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, comment='Whether the tool is enabled for the agent'),
        sa.Column('config', sa.JSON(), nullable=True, comment='Tool-specific configuration for this agent'),
        sa.Column('default_parameters', sa.JSON(), nullable=True, comment='Default parameters for this agent'),
        sa.Column('constraints', sa.JSON(), nullable=True, comment='Usage constraints for this agent'),
        sa.Column('can_execute', sa.Boolean(), nullable=False, comment='Whether agent can execute this tool'),
        sa.Column('max_executions_per_day', sa.Integer(), nullable=True, comment='Maximum executions per day'),
        sa.Column('max_execution_time_seconds', sa.Integer(), nullable=True, comment='Maximum execution time per call'),
        sa.Column('allowed_file_types', sa.JSON(), nullable=True, comment='Allowed file types for file operations'),
        sa.Column('max_file_size_mb', sa.Integer(), nullable=True, comment='Maximum file size in MB for this agent'),
        sa.Column('requires_agent_auth', sa.Boolean(), nullable=False, comment='Whether agent-specific authentication is required'),
        sa.Column('agent_credentials', sa.JSON(), nullable=True, comment='Agent-specific credentials'),
        sa.Column('usage_count', sa.Integer(), nullable=False, comment='Total usage count by this agent'),
        sa.Column('success_count', sa.Integer(), nullable=False, comment='Successful usage count by this agent'),
        sa.Column('error_count', sa.Integer(), nullable=False, comment='Error usage count by this agent'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True, comment='Last usage timestamp by this agent'),
        sa.Column('total_execution_time', sa.Float(), nullable=False, comment='Total execution time in seconds'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True, comment='Rate limit per minute'),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=True, comment='Rate limit per hour'),
        sa.Column('last_rate_limit_reset', sa.DateTime(timezone=True), nullable=True, comment='Last rate limit reset timestamp'),
        sa.Column('current_minute_count', sa.Integer(), nullable=False, comment='Current minute execution count'),
        sa.Column('current_hour_count', sa.Integer(), nullable=False, comment='Current hour execution count'),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True, comment='User who assigned this tool'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Assignment timestamp'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Assignment notes'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was created'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Timestamp when record was last updated'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tool_id'], ['tools.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'pending', 'suspended')", name='check_assignment_status'),
        sa.CheckConstraint('max_executions_per_day IS NULL OR max_executions_per_day > 0', name='check_max_executions_positive'),
        sa.CheckConstraint('max_execution_time_seconds IS NULL OR max_execution_time_seconds > 0', name='check_max_execution_time_positive'),
        sa.CheckConstraint('max_file_size_mb IS NULL OR max_file_size_mb > 0', name='check_max_file_size_positive'),
        sa.CheckConstraint('usage_count >= 0', name='check_usage_count_non_negative'),
        sa.CheckConstraint('success_count >= 0', name='check_success_count_non_negative'),
        sa.CheckConstraint('error_count >= 0', name='check_error_count_non_negative'),
        sa.CheckConstraint('total_execution_time >= 0', name='check_total_execution_time_non_negative'),
        sa.CheckConstraint('rate_limit_per_minute IS NULL OR rate_limit_per_minute > 0', name='check_rate_limit_minute_positive'),
        sa.CheckConstraint('rate_limit_per_hour IS NULL OR rate_limit_per_hour > 0', name='check_rate_limit_hour_positive'),
        sa.CheckConstraint('current_minute_count >= 0', name='check_current_minute_count_non_negative'),
        sa.CheckConstraint('current_hour_count >= 0', name='check_current_hour_count_non_negative'),
        sa.UniqueConstraint('agent_id', 'tool_id', name='uq_agent_tool_assignment'),
        comment='Agent-Tool relationship model representing tool assignments to agents.'
    )
    op.create_index('idx_agent_tools_agent_id', 'agent_tools', ['agent_id'], unique=False)
    op.create_index('idx_agent_tools_tool_id', 'agent_tools', ['tool_id'], unique=False)
    op.create_index('idx_agent_tools_status', 'agent_tools', ['status'], unique=False)
    op.create_index('idx_agent_tools_last_used', 'agent_tools', ['last_used_at'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table('agent_tools')
    op.drop_table('execution_snapshots')
    op.drop_table('workflow_executions')
    op.drop_table('workflow_nodes')
    op.drop_table('tools')
    op.drop_table('workflows')
    op.drop_table('agents')