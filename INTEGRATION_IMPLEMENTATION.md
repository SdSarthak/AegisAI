## Integration & Gap Analysis Implementation Summary

### Overview
This implementation adds per-user Jira and Linear integration settings with automatic ticket creation when AI systems are classified as HIGH or UNACCEPTABLE risk. It also includes a gap analysis endpoint that maps compliance gaps to separate ticketing options.

---

## New Files Created

### 1. **Models** (`backend/app/models/integration.py`)
- `IntegrationSettings`: Stores per-user Jira/Linear credentials and configuration
  - `integration_type`: JIRA or LINEAR
  - `base_url`, `api_key`, `username/team_id`: Connection credentials
  - `project_key` (Jira) / `team_id` (Linear): Target project/team
  - `create_on_high`, `create_on_unacceptable`: Toggle ticket creation per risk level
  - `create_gap_tickets`: Enable separate tickets per compliance gap
  - `gap_ticket_template`: Map gap types to issue types
  - `is_active`, `last_tested_at`, `test_result`: Integration health tracking

- `IntegrationTicket`: Track created tickets linked to systems and gaps
  - `external_ticket_id`: Jira issue key or Linear issue ID
  - `external_url`: Direct link to the ticket
  - `link_reason`: "classification_high", "classification_unacceptable", or "gap_{gap_type}"
  - `gap_type`: Specific gap mapped to this ticket (if applicable)

### 2. **Schemas** (`backend/app/schemas/integration.py`)
- `IntegrationSettingsCreate`: Request payload for creating/updating integrations
- `IntegrationSettingsResponse`: Response excluding credentials
- `ComplianceGap`: Individual gap with severity, description, recommendation, and affected articles
- `GapAnalysisResponse`: Complete gap analysis for a system
- `IntegrationTestResponse`: Connection test result
- `IntegrationTicketResponse`: Created ticket metadata

### 3. **Integration Clients** (`backend/app/modules/integrations/__init__.py`)
- `JiraClient`: REST API client for Jira
  - `test_connection()`: Verify credentials and connectivity
  - `create_issue()`: Create issues with summary, description, labels
  
- `LinearClient`: GraphQL API client for Linear
  - `test_connection()`: Verify API key validity
  - `create_issue()`: Create issues with title, description, priority, labels

### 4. **Gap Analysis Module** (`backend/app/modules/gap_analysis.py`)
- `analyze_gaps()`: Compute compliance gaps based on risk level and questionnaire responses
  - UNACCEPTABLE: Prohibited use gap
  - HIGH: Explainability, oversight, data governance, documentation, risk management, post-market monitoring
  - LIMITED/HIGH: Transparency, synthetic content disclosure
  - General: Fundamental rights impact gaps

- `calculate_compliance_score()`: Compute 0-100 compliance score based on gaps identified

### 5. **Ticket Creator Utility** (`backend/app/modules/ticket_creator.py`)
- `create_tickets_for_classification()`: Main entry point triggered on HIGH/UNACCEPTABLE classification
  - `_create_jira_tickets()`: Creates main classification ticket + gap tickets (if enabled)
  - `_create_linear_tickets()`: Creates main classification ticket + gap tickets (if enabled)
  - Handles credentials from IntegrationSettings
  - Maps gap severity to Jira issue types or Linear priority levels

### 6. **API Endpoints** (`backend/app/api/v1/integrations.py`)
**Base: `/api/v1/integrations`**

- `POST /jira`: Create/update Jira integration
- `POST /linear`: Create/update Linear integration
- `GET /`: List all integrations for current user
- `GET /{integration_id}`: Get specific integration
- `POST /{integration_id}/test`: Test connection to integration
- `DELETE /{integration_id}`: Delete integration
- `GET /{integration_id}/tickets`: List all tickets created by an integration

### 7. **Gap Analysis Endpoint** (`backend/app/api/v1/gap_analysis.py`)
**Base: `/api/v1/gap-analysis`**

- `GET /{system_id}`: Get detailed compliance gap analysis for a system
  - Returns gaps with severity, affected articles, recommendations
  - Calculates overall compliance score
  - Requires system to be classified first

---

## Flow: Classification → Ticket Creation

### 1. User classifies an AI system (`POST /api/v1/classification/classify/{system_id}`)

### 2. Classification endpoint now:
   - Performs risk classification
   - Updates AISystem risk_level and compliance_status
   - Creates RiskAssessment record
   - **NEW**: Calls `create_tickets_for_classification()`

### 3. Ticket creator:
   - Queries user's IntegrationSettings where is_active=True
   - Checks if create_on_high / create_on_unacceptable is enabled
   - For each integration:
     - **Main ticket**: Summarizes classification and gaps
     - **Gap tickets** (if create_gap_tickets=True): Individual tickets per gap
   - Creates IntegrationTicket records tracking external IDs and URLs
   - Errors are logged but don't fail classification

---

## Database Schema

```sql
-- Integration settings per user
CREATE TABLE integration_settings (
  id INTEGER PRIMARY KEY,
  user_id INTEGER FOREIGN KEY,
  integration_type ENUM(jira, linear),
  base_url VARCHAR(500),
  api_key VARCHAR(500),
  username VARCHAR(255),
  project_key VARCHAR(100),
  team_id VARCHAR(100),
  create_on_high BOOLEAN DEFAULT TRUE,
  create_on_unacceptable BOOLEAN DEFAULT TRUE,
  create_gap_tickets BOOLEAN DEFAULT FALSE,
  gap_ticket_template JSON,
  is_active BOOLEAN DEFAULT TRUE,
  last_tested_at DATETIME,
  test_result VARCHAR(1000),
  created_at DATETIME,
  updated_at DATETIME
);

-- Track created tickets
CREATE TABLE integration_tickets (
  id INTEGER PRIMARY KEY,
  integration_id INTEGER FOREIGN KEY,
  ai_system_id INTEGER FOREIGN KEY,
  external_ticket_id VARCHAR(255),
  external_url VARCHAR(500),
  ticket_type VARCHAR(100),
  link_reason VARCHAR(100),
  gap_type VARCHAR(100),
  created_at DATETIME
);
```

---

## API Examples

### 1. Create Jira Integration
```bash
POST /api/v1/integrations/jira
Authorization: Bearer {token}

{
  "integration_type": "jira",
  "base_url": "https://jira.company.com",
  "api_key": "ATATT...",
  "username": "user@company.com",
  "project_key": "COMPLIANCE",
  "create_on_high": true,
  "create_on_unacceptable": true,
  "create_gap_tickets": true,
  "gap_ticket_template": {
    "explainability": "Task",
    "oversight": "Story",
    "data_governance": "Task",
    "documentation": "Bug"
  }
}

Response:
{
  "id": 1,
  "integration_type": "jira",
  "base_url": "https://jira.company.com",
  "project_key": "COMPLIANCE",
  "create_on_high": true,
  "create_on_unacceptable": true,
  "create_gap_tickets": true,
  ...
}
```

### 2. Create Linear Integration
```bash
POST /api/v1/integrations/linear
Authorization: Bearer {token}

{
  "integration_type": "linear",
  "base_url": "https://api.linear.app",
  "api_key": "lin_api_...",
  "team_id": "TEAM-123",
  "create_on_high": true,
  "create_on_unacceptable": true,
  "create_gap_tickets": true,
  "gap_ticket_template": {
    "explainability": "Task",
    "oversight": "Bug"
  }
}
```

### 3. Test Integration Connection
```bash
POST /api/v1/integrations/1/test
Authorization: Bearer {token}

Response:
{
  "success": true,
  "message": "Connected as John Doe",
  "details": {
    "id": "user-id",
    "email": "john@company.com",
    "name": "John Doe"
  }
}
```

### 4. Classify System (triggers ticket creation)
```bash
POST /api/v1/classification/classify/42
Authorization: Bearer {token}

{
  "use_case_category": "hr_recruitment",
  "is_safety_component": false,
  "affects_fundamental_rights": true,
  "hr_recruitment_screening": true,
  ...
}

Response (RiskClassificationResponse):
{
  "risk_level": "high",
  "confidence": 0.95,
  "reasons": [...],
  "requirements": [...],
  "next_steps": [...]
}

// Automatically creates tickets in configured Jira/Linear
```

### 5. Get Gap Analysis
```bash
GET /api/v1/gap-analysis/42
Authorization: Bearer {token}

Response (GapAnalysisResponse):
{
  "ai_system_id": 42,
  "risk_level": "high",
  "compliance_status": "in_progress",
  "overall_compliance_score": 35.0,
  "gaps": [
    {
      "gap_type": "explainability",
      "severity": "high",
      "description": "Lack of documented explainability measures...",
      "recommendation": "Implement explainability mechanisms (LIME, SHAP)...",
      "affected_articles": ["Article 13", "Article 14"]
    },
    {
      "gap_type": "oversight",
      "severity": "high",
      "description": "No human oversight mechanisms documented...",
      "recommendation": "Establish human-in-the-loop processes...",
      "affected_articles": ["Article 14"]
    }
  ],
  "summary": "This High-risk system has 6 compliance gap(s) that need to be addressed.",
  "analysis_date": "2026-05-15T10:30:00Z"
}
```

### 6. List Created Tickets
```bash
GET /api/v1/integrations/1/tickets
Authorization: Bearer {token}

Response:
[
  {
    "id": 1,
    "external_ticket_id": "COMPLIANCE-123",
    "external_url": "https://jira.company.com/browse/COMPLIANCE-123",
    "ticket_type": "Task",
    "link_reason": "classification_high",
    "gap_type": null,
    "created_at": "2026-05-15T10:30:00Z"
  },
  {
    "id": 2,
    "external_ticket_id": "COMPLIANCE-124",
    "external_url": "https://jira.company.com/browse/COMPLIANCE-124",
    "ticket_type": "Task",
    "link_reason": "gap_explainability",
    "gap_type": "explainability",
    "created_at": "2026-05-15T10:30:00Z"
  }
]
```

---

## Model Relationships

```
User (1) ---> (M) IntegrationSettings
User (1) ---> (M) AISystem

IntegrationSettings (1) ---> (M) IntegrationTicket
AISystem (1) ---> (M) IntegrationTicket

IntegrationTicket records which system triggered ticket creation and why
```

---

## Testing

Run integration tests:
```bash
pytest backend/tests/test_integrations.py -v
```

Tests cover:
- Creating Jira and Linear integrations
- Listing, retrieving, and deleting integrations
- Gap analysis endpoint
- Error handling for unclassified systems

---

## Security Considerations

1. **API Keys**: Stored as plaintext (consider encryption at rest in production)
2. **Credentials**: Only shown during creation; hidden in responses
3. **User Scope**: Each integration is user-scoped; users can only manage their own
4. **Error Handling**: Integration failures don't block classification workflow
5. **Rate Limiting**: Recommended for external API calls

---

## Migration Steps

1. Run database migrations to create new tables:
   - `integration_settings`
   - `integration_tickets`

2. Add `integrations` relationship to User model (already done)

3. Register new routers in API v1 init (already done)

4. Update requirements.txt with any new dependencies (requests is likely already included)

---

## Future Enhancements

1. **Encryption**: Encrypt API keys at rest
2. **Webhook Sync**: Listen for ticket updates and sync compliance status
3. **Template Engine**: Allow Jira/Linear templates for ticket descriptions
4. **Bulk Retry**: Manually retry failed integrations
5. **Audit Logging**: Log all integration operations
6. **Rate Limiting**: Per-integration API rate limiting
7. **Custom Fields**: Support for Jira/Linear custom fields
