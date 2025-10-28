### Summary
Added starter code for legacy platform management to support Samsung Bada refactoring, including platform lifecycle management, incident mapping, and migration capabilities.

### Context
This change addresses the Samsung Bada refactoring requirement from Planview AgilePlace. Samsung Bada was a discontinued mobile platform that requires special handling for legacy incidents. This refactoring introduces a structured approach to:
- Manage platform lifecycle (active, deprecated, discontinued, legacy)
- Handle platform-specific incident mappings
- Support migration from discontinued platforms (e.g., Bada to Tizen)
- Track legacy device information

### Implementation

**New Files Created:**
1. **`src/models/platform.py`** - Platform data models
   - `PlatformType` enum: Defines platform types (Bada, Tizen, Android, iOS, Web)
   - `PlatformStatus` enum: Lifecycle states (active, deprecated, discontinued, legacy)
   - `DevicePlatform`: Core platform configuration model
   - `PlatformIncidentMapping`: Links incidents to specific platforms
   - `PlatformMigrationRequest/Response`: Migration operation models

2. **`src/services/platform_service.py`** - Platform management service
   - `PlatformService`: Main service class with audit logging integration
   - Initializes Samsung Bada 2.0 as a discontinued legacy platform
   - Methods for platform registration, querying, and lifecycle management
   - Migration support for moving incidents between platforms
   - Platform deprecation workflow

3. **`tests/test_platform_service.py`** - Comprehensive test suite
   - 15 test cases covering all platform service functionality
   - Tests for Bada initialization, registration, filtering, mapping
   - Migration tests (dry-run and actual)
   - Platform deprecation workflow tests

**Modified Files:**
1. **`src/api/endpoints.py`** - Added Platform Management endpoints
   - `POST /api/v1/platforms/register` - Register new platforms
   - `GET /api/v1/platforms` - List platforms with filters
   - `GET /api/v1/platforms/legacy` - Get legacy platforms
   - `GET /api/v1/platforms/{platform_id}` - Get platform details
   - `POST /api/v1/platforms/migrate` - Migrate incidents between platforms
   - `POST /api/v1/platforms/{platform_id}/deprecate` - Deprecate platform
   - Added `_platform_service` singleton initialization
   - Added `get_platform_service()` dependency function

### Key Features
- **Samsung Bada Support**: Pre-configured Bada 2.0 platform marked as discontinued
- **Migration Path**: Built-in support for Bada → Tizen migration
- **Audit Integration**: All platform operations are auditable
- **RESTful API**: 6 new endpoints following existing patterns
- **Comprehensive Testing**: 15 unit tests with pytest fixtures

### Test Notes
**To verify this implementation:**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run platform service tests:**
   ```bash
   pytest tests/test_platform_service.py -v
   ```

3. **Start the API server:**
   ```bash
   python main.py
   ```

4. **Test the new endpoints:**
   ```bash
   # Get legacy platforms (should include Bada)
   curl http://localhost:8000/api/v1/platforms/legacy
   
   # Get Bada platform details
   curl http://localhost:8000/api/v1/platforms/platform_bada_20
   
   # Test migration (dry-run)
   curl -X POST http://localhost:8000/api/v1/platforms/migrate \
     -H "Content-Type: application/json" \
     -d '{
       "source_platform": "bada",
       "target_platform": "tizen",
       "incident_ids": ["INC-123"],
       "dry_run": true
     }'
   ```

5. **View API documentation:**
   - Navigate to `http://localhost:8000/docs`
   - Explore the "Platform Management" tag for all new endpoints

### Design Decisions
- **Stub Implementation**: Service methods are stubs ready for production logic
- **Consistent Patterns**: Follows existing service/model/endpoint architecture
- **Backward Compatible**: No changes to existing functionality
- **Extensible**: Easy to add new platform types or migration paths

### Next Steps (Future Work)
- Implement actual migration logic with database persistence
- Add bulk migration endpoints
- Create platform analytics and reporting
- Add platform-specific resolution strategies
- Implement automated platform sunset workflows
