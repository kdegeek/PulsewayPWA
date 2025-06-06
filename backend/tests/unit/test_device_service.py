import unittest
from unittest.mock import MagicMock, patch, call, ANY
from sqlalchemy import func # Required for func.count
from backend.app.services.device_service import DeviceService
from backend.app.models.database import Device # Assuming Device model has these attributes
from backend.app.models.dto import DeviceFilters

class TestDeviceService(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_pulseway_client = MagicMock()
        self.service = DeviceService(self.mock_db, self.mock_pulseway_client)

    def _assert_filters_applied(self, mock_query, expected_filters):
        """Helper function to assert that the correct filters were applied."""
        for expected_filter in expected_filters:
            # This is a simplified check. In a real scenario, you might need a more robust way
            # to inspect SQLAlchemy filter expressions.
            self.assertTrue(
                any(
                    # Comparing string representations of calls, which is brittle.
                    # A better approach would be to use a library or custom matcher
                    # that understands SQLAlchemy expressions.
                    str(expected_filter.compile(compile_kwargs={"literal_binds": True})) in str(call_args)
                    for call_args in mock_query.filter.call_args_list
                ),
                f"Expected filter {expected_filter} not applied. Applied filters: {mock_query.filter.call_args_list}"
            )


    def test_get_devices_with_filters_no_filters(self):
        mock_query = self.mock_db.query.return_value
        mock_offset = mock_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='1', name='Test Device')]

        filters = DeviceFilters()
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'Test Device')
        self.mock_db.query.assert_called_once_with(Device)
        mock_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)
        mock_query.filter.assert_not_called() # No filters should be applied

    def test_get_devices_with_filters_by_organization(self):
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value # After first filter
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='2', name='Org Device', organization_name='Test Org')]

        filters = DeviceFilters(organization="Test Org")
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].organization_name, 'Test Org')
        self.mock_db.query.assert_called_once_with(Device)
        mock_query.filter.assert_called_once() # Ensure filter is called
        # self._assert_filters_applied(mock_query, [Device.organization_name == "Test Org"]) # More precise check
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)


    def test_get_devices_with_filters_by_site(self):
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='3', name='Site Device', site_name='Test Site')]

        filters = DeviceFilters(site="Test Site")
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].site_name, 'Test Site')
        self.mock_db.query.assert_called_once_with(Device)
        mock_query.filter.assert_called_once()
        # self._assert_filters_applied(mock_query, [Device.site_name == "Test Site"])
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    def test_get_devices_with_filters_by_group(self):
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='4', name='Group Device', group_name='Test Group')]

        filters = DeviceFilters(group="Test Group")
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].group_name, 'Test Group')
        mock_query.filter.assert_called_once()
        # self._assert_filters_applied(mock_query, [Device.group_name == "Test Group"])
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    def test_get_devices_with_filters_online_only(self):
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='5', name='Online Device', online=True)]

        filters = DeviceFilters(online_only=True)
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].online)
        mock_query.filter.assert_called_once()
        # self._assert_filters_applied(mock_query, [Device.online == True])
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    def test_get_devices_with_filters_offline_only(self):
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='6', name='Offline Device', online=False)]

        filters = DeviceFilters(offline_only=True)
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].online)
        mock_query.filter.assert_called_once()
        # self._assert_filters_applied(mock_query, [Device.online == False])
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)


    def test_get_devices_with_filters_has_alerts(self):
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='7', name='Alert Device', has_alerts=True)]

        filters = DeviceFilters(has_alerts=True)
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].has_alerts)
        mock_query.filter.assert_called_once()
        # self._assert_filters_applied(mock_query, [Device.has_alerts == True])
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    def test_get_devices_with_filters_computer_type(self):
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='8', name='Laptop Device', computer_type='Laptop')]

        filters = DeviceFilters(computer_type='Laptop')
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].computer_type, 'Laptop')
        mock_query.filter.assert_called_once()
        # self._assert_filters_applied(mock_query, [Device.computer_type == 'Laptop'])
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    def test_get_devices_with_filters_combination(self):
        mock_query = self.mock_db.query.return_value
        # Simulate multiple calls to filter
        mock_filtered_query1 = mock_query.filter.return_value
        mock_filtered_query2 = mock_filtered_query1.filter.return_value
        mock_offset = mock_filtered_query2.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='9', name='Combo Device', organization_name='Combo Org', online=True, computer_type='Desktop')]

        filters = DeviceFilters(organization="Combo Org", online_only=True, computer_type="Desktop")
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].organization_name, 'Combo Org')
        self.assertTrue(result[0].online)
        self.assertEqual(result[0].computer_type, 'Desktop')

        self.assertEqual(mock_query.filter.call_count, 3) # Called for org, online, and computer_type
        # self._assert_filters_applied(mock_query, [
        #     Device.organization_name == "Combo Org",
        #     Device.online == True,
        #     Device.computer_type == "Desktop"
        # ])
        mock_filtered_query2.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    def test_get_devices_with_filters_pagination(self):
        mock_query = self.mock_db.query.return_value
        mock_offset = mock_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='10', name='Paginated Device')]

        filters = DeviceFilters(page=2, page_size=50)
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        mock_query.offset.assert_called_once_with(50) # (page 2 - 1) * page_size 50
        mock_offset.limit.assert_called_once_with(50)

    def test_get_devices_with_filters_online_and_offline_conflict(self):
        # online_only and offline_only are mutually exclusive.
        # The service should probably prioritize one or raise an error.
        # Assuming it prioritizes online_only if both are true.
        mock_query = self.mock_db.query.return_value
        mock_filtered_query = mock_query.filter.return_value
        mock_offset = mock_filtered_query.offset.return_value
        mock_limit = mock_offset.limit.return_value
        mock_limit.all.return_value = [Device(id='11', name='Online Device Conflict', online=True)]

        filters = DeviceFilters(online_only=True, offline_only=True)
        result = self.service.get_devices_with_filters(filters)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].online)
        mock_query.filter.assert_called_once() # Should only apply one of the online filters
        # self._assert_filters_applied(mock_query, [Device.online == True])
        mock_filtered_query.offset.assert_called_once_with(0)
        mock_offset.limit.assert_called_once_with(100)

    # --- Tests for get_device_statistics ---

    def test_get_device_statistics_no_devices(self):
        # Mock for count queries
        mock_count_query = MagicMock()
        mock_count_query.scalar.return_value = 0 # For total_devices_with_agent query
        mock_count_query.count.return_value = 0 # For all other .count() calls

        # Mock for group_by queries
        mock_group_query = MagicMock()
        mock_group_query.all.return_value = []

        def query_side_effect(*args, **kwargs):
            # Differentiate based on what's being queried.
            # This is a simplified check; in reality, you might inspect args more closely.
            # If the first argument is Device, it's likely one of the .count() queries
            if args and args[0] == Device:
                # Further differentiate if it's the specific query for devices_with_agent
                # This requires knowing the exact structure of that query in the service.
                # For this example, let's assume the service does a specific filter for agent_status.
                # We'll make a more general mock here and refine if needed.
                # The .filter().count() pattern
                filtered_mock = MagicMock()
                filtered_mock.count.return_value = 0

                # The .filter().scalar() pattern (for devices_with_agent)
                # We need to ensure that if .filter is called, and then .scalar, it returns 0
                # This part is tricky without seeing the exact DeviceService code.
                # Let's assume a general count_query for now.
                # If a filter for agent_status is applied, then count is called.

                # A simplified approach: if .filter is called on mock_count_query,
                # return another mock that has a .count() method.

                # Let's refine the side_effect for self.mock_db.query.return_value.filter.return_value.count
                # This is getting complex. A better way is to mock the final call in the chain.

                # For queries like self.db.query(Device).count()
                # For self.db.query(Device).filter(...).count()
                # For self.db.query(func.count(Device.id)).filter(Device.agent_status == "operational").scalar()

                # Let's assume the .count() method is called on a query object
                # and .scalar() is called on another.
                # We can make the main query mock return itself for filter calls, then specify count/scalar.

                main_query_mock = MagicMock()
                main_query_mock.count.return_value = 0 # Default for most counts

                # Specific for devices_with_agent if it uses a different pattern like scalar()
                # This needs to align with how DeviceService calls it.
                # Example: query(func.count(Device.id)).filter(...).scalar()
                # So, if query is called with func.count, it should return a mock that can be filtered and then scalar called.

                # If query is called with Device directly (e.g., query(Device).count())
                if len(args) == 1 and args[0] == Device:
                    # This handles total_devices, online_devices, critical_alerts, elevated_alerts
                    _mock_q = MagicMock()
                    # if it's filtered for online, critical, elevated
                    _filter_mock = MagicMock()
                    _filter_mock.count.return_value = 0
                    _mock_q.filter.return_value = _filter_mock
                    _mock_q.count.return_value = 0 # For total_devices without filter
                    return _mock_q

                # If query is for devices_with_agent (func.count)
                # This is a rough approximation.
                if args and isinstance(args[0], type(func.count(Device.id))): # Check if it's a func.count object
                     _mock_func_count_query = MagicMock()
                     _filtered_func_count_query = MagicMock()
                     _filtered_func_count_query.scalar.return_value = 0
                     _mock_func_count_query.filter.return_value = _filtered_func_count_query
                     return _mock_func_count_query

                return main_query_mock # Fallback for Device based queries


            # For group_by queries like self.db.query(Device.organization_name, func.count(Device.id))...
            elif args and len(args) > 1 and isinstance(args[1], type(func.count(Device.id))):
                _mock_group_q = MagicMock()
                _group_by_mock = MagicMock()
                _group_by_mock.all.return_value = []
                _mock_group_q.group_by.return_value = _group_by_mock
                return _mock_group_q

            return MagicMock() # Default fallback

        self.mock_db.query.side_effect = query_side_effect

        stats = self.service.get_device_statistics()

        self.assertEqual(stats['total_devices'], 0)
        self.assertEqual(stats['online_devices'], 0)
        self.assertEqual(stats['offline_devices'], 0)
        self.assertEqual(stats['devices_with_agent'], 0)
        self.assertEqual(stats['devices_without_agent'], 0)
        self.assertEqual(stats['critical_alerts'], 0)
        self.assertEqual(stats['elevated_alerts'], 0)
        self.assertEqual(stats['devices_by_organization'], {})
        self.assertEqual(stats['devices_by_site'], {})
        self.assertEqual(stats['devices_by_type'], {})

    def test_get_device_statistics_with_data(self):
        # --- Mock setup ---
        # This function will be the side_effect for self.mock_db.query
        def query_side_effect(*args, **kwargs):
            # Query for counts (e.g., total_devices, online_devices)
            if args and args[0] == Device:
                mock_main_query = MagicMock()

                # Mock for .count() directly on query(Device) -> total_devices
                mock_main_query.count.return_value = 15 # total_devices

                # Mock for .filter().count()
                mock_filtered_query = MagicMock()

                # Based on filter arguments, return different counts
                # This requires inspecting the filter criteria.
                # For simplicity, we'll use a list of side_effects for count if filter is called.
                # This assumes a specific order of filter().count() calls in the service method
                # Order: online_devices, devices_with_agent (if it uses filter().count()), critical_alerts, elevated_alerts
                # This is fragile. A better way is to inspect call_args of filter.

                # Let's assume:
                # query(Device).filter(Device.online == True).count() -> online_devices
                # query(Device).filter(Device.has_alerts == True, Device.alert_severity == 'critical').count() -> critical_alerts
                # query(Device).filter(Device.has_alerts == True, Device.alert_severity == 'elevated').count() -> elevated_alerts

                # For online_devices
                # if str(Device.online == True) in str(mock_main_query.filter.call_args):
                # This is hard to do directly in side_effect without more context.
                # Instead, we can have multiple mock objects returned by filter.

                def filter_side_effect(condition):
                    # We need to return a mock that has a count method.
                    _m = MagicMock()
                    if str(condition) == str(Device.online == True): # Simplified comparison
                        _m.count.return_value = 10 # online_devices
                    elif str(condition) == str(Device.agent_status == "operational"): # devices_with_agent (if by filter().count())
                         _m.count.return_value = 12 # This is an assumption on how devices_with_agent is counted
                    elif str(condition) == str(Device.has_alerts == True): # This could be for critical or elevated
                        # This needs to be more specific if there are chained filters
                        # For now, let's assume critical/elevated are handled by func.count() path
                        _m.count.return_value = 0 # Default for has_alerts alone
                    else: # Default for any other filter
                        _m.count.return_value = 0
                    return _m

                mock_main_query.filter.side_effect = filter_side_effect
                return mock_main_query

            # Query for devices_with_agent (func.count...scalar)
            # query(func.count(Device.id)).filter(Device.agent_status == "operational").scalar()
            elif args and isinstance(args[0], type(func.count(Device.id))) and not kwargs.get('group_by_arg', False):
                mock_func_query = MagicMock()
                mock_filtered_func_query = MagicMock()
                # Assuming this is the call for devices_with_agent
                mock_filtered_func_query.scalar.return_value = 12 # devices_with_agent
                mock_func_query.filter.return_value = mock_filtered_func_query
                return mock_func_query

            # Query for critical_alerts (func.count...scalar)
            # query(func.count(Device.id)).filter(Device.has_alerts == True, Device.alert_severity == 'critical').scalar()
            # This part is tricky because func.count(Device.id) is used for multiple stats.
            # We need to differentiate based on the filter applied AFTER query(func.count(Device.id))
            # This means the side_effect for filter needs to be smart.

            # Let's make a general mock for func.count().filter().scalar()
            # The differentiation will happen on the .filter().scalar() part.
            # This side_effect is for self.mock_db.query
            if args and isinstance(args[0], type(func.count(Device.id))): # General func.count queries
                _mock_func_count_base = MagicMock()
                _mock_filtered_scalar = MagicMock()

                def func_filter_side_effect(*filter_args):
                    # Example: filter_args could be (Device.has_alerts == True, Device.alert_severity == 'critical')
                    # This is very simplified. Real comparison of SQLAlchemy conditions is complex.
                    if any("agent_status" in str(fa) for fa in filter_args):
                         _mock_filtered_scalar.scalar.return_value = 12 # devices_with_agent
                    elif any("critical" in str(fa) for fa in filter_args):
                         _mock_filtered_scalar.scalar.return_value = 3 # critical_alerts
                    elif any("elevated" in str(fa) for fa in filter_args):
                         _mock_filtered_scalar.scalar.return_value = 4 # elevated_alerts
                    else:
                         _mock_filtered_scalar.scalar.return_value = 0
                    return _mock_filtered_scalar

                _mock_func_count_base.filter.side_effect = func_filter_side_effect
                return _mock_func_count_base


            # Queries for grouped statistics (e.g., devices_by_organization)
            # query(Device.organization_name, func.count(Device.id)).group_by(...).all()
            elif args and len(args) > 1 and isinstance(args[1], type(func.count(Device.id))):
                mock_group_query = MagicMock()
                mock_group_by_collector = MagicMock()

                if args[0] == Device.organization_name:
                    mock_group_by_collector.all.return_value = [
                        ('Org A', 7), ('Org B', 5), (None, 3) # devices_by_organization (None becomes 'Unknown')
                    ]
                elif args[0] == Device.site_name:
                    mock_group_by_collector.all.return_value = [
                        ('Site X', 8), ('Site Y', 4), (None, 3) # devices_by_site
                    ]
                elif args[0] == Device.computer_type:
                     mock_group_by_collector.all.return_value = [
                        ('Server', 9), ('Workstation', 5), (None, 1) # devices_by_type
                    ]
                else:
                    mock_group_by_collector.all.return_value = []

                mock_group_query.group_by.return_value = mock_group_by_collector
                # Also handle label if service uses it, e.g. .label('count')
                mock_group_query.label.return_value = args[1] # return the func.count object itself
                return mock_group_query

            # Fallback if no other condition met
            return MagicMock()

        self.mock_db.query.side_effect = query_side_effect

        # --- Call the service method ---
        stats = self.service.get_device_statistics()

        # --- Assertions ---
        self.assertEqual(stats['total_devices'], 15)
        self.assertEqual(stats['online_devices'], 10) # This requires filter(Device.online==True).count() to be 10
        self.assertEqual(stats['offline_devices'], 5)  # 15 (total) - 10 (online)
        self.assertEqual(stats['devices_with_agent'], 12)
        self.assertEqual(stats['devices_without_agent'], 3) # 15 (total) - 12 (with agent)
        self.assertEqual(stats['critical_alerts'], 3)
        self.assertEqual(stats['elevated_alerts'], 4)

        self.assertEqual(stats['devices_by_organization'].get('Org A'), 7)
        self.assertEqual(stats['devices_by_organization'].get('Org B'), 5)
        self.assertEqual(stats['devices_by_organization'].get('Unknown'), 3)

        self.assertEqual(stats['devices_by_site'].get('Site X'), 8)
        self.assertEqual(stats['devices_by_site'].get('Site Y'), 4)
        self.assertEqual(stats['devices_by_site'].get('Unknown'), 3)

        self.assertEqual(stats['devices_by_type'].get('Server'), 9)
        self.assertEqual(stats['devices_by_type'].get('Workstation'), 5)
        self.assertEqual(stats['devices_by_type'].get('Unknown'), 1)

        # Verify calls (example for total_devices and one group_by)
        # Check that query(Device).count() was called for total_devices
        # Check for query(Device.organization_name, func.count(Device.id)).group_by(...).all()

        # Example of specific call verification (can be complex due to side_effect)
        # self.mock_db.query.assert_any_call(Device) # For total devices & online devices count
        # self.mock_db.query.assert_any_call(func.count(Device.id)) # For agent, critical, elevated counts
        # self.mock_db.query.assert_any_call(Device.organization_name, func.count(Device.id)) # For by_org
        # self.mock_db.query.assert_any_call(Device.site_name, func.count(Device.id)) # For by_site
        # self.mock_db.query.assert_any_call(Device.computer_type, func.count(Device.id)) # For by_type

        # It's important that the side_effect function correctly routes calls to the right mocks.
        # The assertions on the final statistics dictionary are the primary validation here.

from datetime import datetime, timezone # Added timezone for offset-aware datetimes

# (other imports remain the same)
# Assuming Notification and DeviceAsset are in backend.app.models.database
from backend.app.models.database import Notification, DeviceAsset

class TestDeviceService(unittest.TestCase):
    # (setUp and other test methods remain the same)

    # --- Tests for get_device_details ---

    def test_get_device_details_found(self):
        # Reset side_effect for this test if it was set by other tests
        self.mock_db.query.side_effect = None

        mock_device_data = {"identifier": "test_id_1", "name": "Test Device 1", "ip_address": "192.168.1.100"}
        mock_device = Device(**mock_device_data) # Assuming Device can be instantiated like this

        # Configure the mock chain: query(Device).filter(...).first()
        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_filter_obj.first.return_value = mock_device # Crucial part: mock the .first() call

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        # It's important that filter is called with an argument that evaluates to True for Device.identifier == "test_id_1"
        # For robust testing, one might use a custom matcher for the filter argument.
        # For simplicity, we'll assume Device.identifier has a __eq__ that works with MagicMock comparisons or ANY.
        # Or, ensure the service code `Device.identifier == device_id` is correctly mocked.

        device_id = "test_id_1"
        returned_device = self.service.get_device_details(device_id)

        self.assertEqual(returned_device, mock_device)
        self.mock_db.query.assert_called_once_with(Device)
        # Example: mock_query_obj.filter.assert_called_once_with(Device.identifier == device_id)
        # This requires Device.identifier to be a mockable object or use ANY with a custom check.
        # For now, we'll check that filter().first() was called.
        mock_query_obj.filter.assert_called_once()
        mock_filter_obj.first.assert_called_once()

    def test_get_device_details_not_found(self):
        self.mock_db.query.side_effect = None # Reset side_effect

        # Configure the mock chain for not found
        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_filter_obj.first.return_value = None # Device not found

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj

        device_id = "non_existent_id"
        returned_device = self.service.get_device_details(device_id)

        self.assertIsNone(returned_device)
        self.mock_db.query.assert_called_once_with(Device)
        mock_query_obj.filter.assert_called_once()
        mock_filter_obj.first.assert_called_once()

    # --- Tests for refresh_single_device_data ---

    @patch('backend.app.services.device_service.datetime')
    def test_refresh_single_device_data_success(self, mock_dt):
        mock_now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = mock_now
        # Also mock fromisoformat if it's used directly on datetime.datetime
        # For Python 3.7+, fromisoformat is a class method on datetime.
        # If the service code uses `datetime.fromisoformat`, this mock is fine.
        # If it uses `datetime.datetime.fromisoformat`, then `mock_dt.datetime.fromisoformat` might be needed.
        # Assuming `from backend.app.services.device_service import datetime` or `import datetime`
        # and then `datetime.fromisoformat` is used.

        device_identifier = "pulseway_id_123"
        pulseway_api_data = {
            'Data': {
                'Id': 123, # This is usually the Pulseway internal ID, not our identifier
                'Name': 'Updated Device Name',
                'IsOnline': True,
                'AgentVersion': '6.2.1',
                'IPAddresses': '192.168.1.100, 10.0.0.5',
                'PublicIPAddresses': '8.8.8.8',
                'Description': 'Updated Description',
                'LastSeenOnline': '2023-10-26T10:00:00Z', # ISO format
                'OsType': 'Windows',
                'OsName': 'Windows Server 2019',
                'CpuUsage': 75.5,
                'MemoryUsage': 60.2,
                'FreeDiskSpace': 120.5, # GB
                'TotalDiskSpace': 500.0, # GB
                'CpuName': 'Intel Xeon',
                'RamSize': 16384, # MB
                'SystemGroupName': 'Servers', # Corresponds to group_name
                'OrganizationName': 'Client Org X', # Corresponds to organization_name
                'SiteName': 'Main Office', # Corresponds to site_name
                # Assume other relevant fields from Pulseway exist here
            }
        }
        self.mock_pulseway_client.get_device.return_value = pulseway_api_data

        existing_device = Device(
            identifier=device_identifier,
            name="Old Device Name",
            is_online=False,
            # Initialize other fields to ensure they are updated
            agent_version="6.0.0",
            ip_address="192.168.1.99",
            public_ip_address="9.9.9.9",
            description="Old Description",
            last_seen_online=datetime(2023,1,1, tzinfo=timezone.utc),
            os_type="Linux",
            os_name="Ubuntu",
            cpu_usage=10.0,
            memory_usage=20.0,
            free_disk_space=100.0,
            total_disk_space=400.0,
            cpu_name="AMD Ryzen",
            ram_size=8192,
            group_name="Old Group",
            organization_name="Old Org",
            site_name="Old Site",
            updated_at=datetime(2023,1,1, tzinfo=timezone.utc)
        )

        self.mock_db.query.side_effect = None # Ensure no complex side effect from other tests
        self.mock_db.query.return_value.filter.return_value.first.return_value = existing_device

        result = self.service.refresh_single_device_data(device_identifier)

        self.assertEqual(result, {"status": "success", "message": "Device data refreshed successfully."})
        self.mock_pulseway_client.get_device.assert_called_once_with(device_identifier)
        self.mock_db.query.assert_called_once_with(Device)
        # Check filter was called with Device.identifier == device_identifier
        # This requires Device.identifier to be comparable or use ANY
        actual_filter_call = self.mock_db.query.return_value.filter.call_args[0][0]
        # self.assertEqual(str(actual_filter_call), str(Device.identifier == device_identifier)) # This can be tricky

        self.mock_db.query.return_value.filter.return_value.first.assert_called_once()

        # Assertions on updated fields
        self.assertEqual(existing_device.name, 'Updated Device Name')
        self.assertEqual(existing_device.is_online, True)
        self.assertEqual(existing_device.agent_version, '6.2.1')
        self.assertEqual(existing_device.ip_address, '192.168.1.100, 10.0.0.5') # Assuming service stores it as received
        self.assertEqual(existing_device.public_ip_address, '8.8.8.8')
        self.assertEqual(existing_device.description, 'Updated Description')
        self.assertEqual(existing_device.last_seen_online, datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(existing_device.os_type, 'Windows')
        self.assertEqual(existing_device.os_name, 'Windows Server 2019')
        self.assertEqual(existing_device.cpu_usage, 75.5)
        self.assertEqual(existing_device.memory_usage, 60.2)
        self.assertEqual(existing_device.free_disk_space, 120.5)
        self.assertEqual(existing_device.total_disk_space, 500.0)
        self.assertEqual(existing_device.cpu_name, 'Intel Xeon')
        self.assertEqual(existing_device.ram_size, 16384)
        self.assertEqual(existing_device.group_name, 'Servers')
        self.assertEqual(existing_device.organization_name, 'Client Org X')
        self.assertEqual(existing_device.site_name, 'Main Office')
        self.assertEqual(existing_device.updated_at, mock_now) # Check updated_at

        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(existing_device)
        self.mock_db.rollback.assert_not_called()

    def test_refresh_single_device_data_not_in_pulseway(self):
        self.mock_db.query.side_effect = None
        device_identifier = "unknown_pulseway_id"
        self.mock_pulseway_client.get_device.return_value = {'Data': {}} # Empty data dict

        result = self.service.refresh_single_device_data(device_identifier)

        self.assertEqual(result, {"status": "error", "message": f"Device with ID {device_identifier} not found in Pulseway or no data returned."})
        self.mock_pulseway_client.get_device.assert_called_once_with(device_identifier)
        self.mock_db.query.assert_not_called() # DB should not be queried if Pulseway fetch fails first
        self.mock_db.commit.assert_not_called()
        self.mock_db.rollback.assert_not_called()

    def test_refresh_single_device_data_not_in_local_db(self):
        self.mock_db.query.side_effect = None
        device_identifier = "pulseway_id_exists_locally_not"
        pulseway_api_data = {'Data': {'Id': 456, 'Name': 'Device Exists in Pulseway'}}
        self.mock_pulseway_client.get_device.return_value = pulseway_api_data

        self.mock_db.query.return_value.filter.return_value.first.return_value = None # Not found in local DB

        result = self.service.refresh_single_device_data(device_identifier)

        expected_message = f"Device with identifier {device_identifier} not found in local database."
        self.assertEqual(result, {"status": "error", "message": expected_message})
        self.mock_pulseway_client.get_device.assert_called_once_with(device_identifier)
        self.mock_db.query.assert_called_once_with(Device)
        self.mock_db.query.return_value.filter.return_value.first.assert_called_once()
        self.mock_db.commit.assert_not_called()
        self.mock_db.rollback.assert_not_called() # Rollback might not be called if only a select fails

    def test_refresh_single_device_data_pulseway_api_exception(self):
        self.mock_db.query.side_effect = None
        device_identifier = "api_fail_id"
        self.mock_pulseway_client.get_device.side_effect = Exception("Pulseway API Error")

        result = self.service.refresh_single_device_data(device_identifier)

        self.assertIn("Error refreshing device data from Pulseway API", result["message"])
        self.assertEqual(result["status"], "error")
        self.mock_pulseway_client.get_device.assert_called_once_with(device_identifier)
        self.mock_db.query.assert_not_called() # Should not query DB if API fails
        self.mock_db.commit.assert_not_called()
        # Depending on service logic, rollback might be called in a general try-except for the whole operation
        # If the exception is caught before DB operations start, rollback might not be needed.
        # Assuming a top-level try-except in the service method that calls rollback.
        # self.mock_db.rollback.assert_called_once() # This depends on service implementation detail.
                                                 # If service doesn't start a transaction before API call,
                                                 # then rollback might not be called.
                                                 # For now, let's assume no rollback if API call is the first thing that fails.
        self.mock_db.rollback.assert_not_called()


    @patch('backend.app.services.device_service.datetime')
    def test_refresh_single_device_data_db_commit_exception(self, mock_dt):
        self.mock_db.query.side_effect = None
        mock_now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = mock_now

        device_identifier = "db_fail_id"
        pulseway_api_data = {'Data': {'Id': 789, 'Name': 'DB Fail Device'}}
        self.mock_pulseway_client.get_device.return_value = pulseway_api_data

        existing_device = Device(identifier=device_identifier, name="Old Name")
        self.mock_db.query.return_value.filter.return_value.first.return_value = existing_device
        self.mock_db.commit.side_effect = Exception("DB Commit Error")

        result = self.service.refresh_single_device_data(device_identifier)

        self.assertEqual(result["status"], "error")
        self.assertIn("Database error during device data refresh", result["message"])

        self.mock_pulseway_client.get_device.assert_called_once_with(device_identifier)
        self.mock_db.query.assert_called_once_with(Device)
        self.mock_db.commit.assert_called_once()
        self.mock_db.rollback.assert_called_once() # Rollback should be called on commit failure
        self.mock_db.refresh.assert_not_called() # Refresh would not be called if commit fails


    @patch('backend.app.services.device_service.datetime')
    def test_refresh_single_device_data_invalid_date_format(self, mock_dt):
        self.mock_db.query.side_effect = None
        mock_now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = mock_now

        device_identifier = "invalid_date_id"
        pulseway_api_data = {
            'Data': {
                'Id': 101,
                'Name': 'Invalid Date Device',
                'LastSeenOnline': 'Not a valid date string', # Invalid date
                'IsOnline': True
            }
        }
        self.mock_pulseway_client.get_device.return_value = pulseway_api_data

        original_last_seen = datetime(2022, 1, 1, tzinfo=timezone.utc)
        existing_device = Device(identifier=device_identifier, name="Old Name", last_seen_online=original_last_seen)
        self.mock_db.query.return_value.filter.return_value.first.return_value = existing_device

        result = self.service.refresh_single_device_data(device_identifier)

        self.assertEqual(result, {"status": "success", "message": "Device data refreshed successfully."})

        # Check that name was updated, but last_seen_online was not (or handled gracefully)
        self.assertEqual(existing_device.name, 'Invalid Date Device')
        self.assertEqual(existing_device.is_online, True)
        # Assert that last_seen_online remains original value if service skips invalid date
        # This depends on the service's error handling for date parsing.
        # Assuming it logs an error and skips updating the field, or sets it to None.
        # If it's skipped, it should retain its original value.
        self.assertEqual(existing_device.last_seen_online, original_last_seen)
        # Or, if the service sets it to None on parsing error:
        # self.assertIsNone(existing_device.last_seen_online)

        self.assertEqual(existing_device.updated_at, mock_now)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(existing_device)
        self.mock_db.rollback.assert_not_called()

    @patch('backend.app.services.device_service.datetime')
    def test_refresh_single_device_data_missing_date_field(self, mock_dt):
        self.mock_db.query.side_effect = None
        mock_now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = mock_now

        device_identifier = "missing_date_id"
        pulseway_api_data = {
            'Data': { # 'LastSeenOnline' is missing
                'Id': 102,
                'Name': 'Missing Date Device',
                'IsOnline': False
            }
        }
        self.mock_pulseway_client.get_device.return_value = pulseway_api_data

        original_last_seen = datetime(2022, 1, 1, tzinfo=timezone.utc)
        existing_device = Device(identifier=device_identifier, name="Old Name", last_seen_online=original_last_seen)
        self.mock_db.query.return_value.filter.return_value.first.return_value = existing_device

        result = self.service.refresh_single_device_data(device_identifier)
        self.assertEqual(result, {"status": "success", "message": "Device data refreshed successfully."})
        self.assertEqual(existing_device.name, 'Missing Date Device')
        # last_seen_online should remain unchanged if the field is missing from API response
        self.assertEqual(existing_device.last_seen_online, original_last_seen)
        self.assertEqual(existing_device.updated_at, mock_now)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(existing_device)

    # --- Tests for search and retrieval methods ---

    def test_search_devices_by_term(self):
        self.mock_db.query.side_effect = None
        mock_devices = [Device(name="Server Alpha", identifier="s1"), Device(description="Workstation Alpha", identifier="w1")]

        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_limit_obj = MagicMock()
        mock_offset_obj = MagicMock() # Added for completeness, assuming offset might be used

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        mock_filter_obj.offset.return_value = mock_offset_obj # offset before limit
        mock_offset_obj.limit.return_value = mock_limit_obj
        mock_limit_obj.all.return_value = mock_devices

        search_term = "Alpha"
        limit_val = 10
        offset_val = 0
        result = self.service.search_devices_by_term(search_term, limit=limit_val, offset=offset_val)

        self.assertEqual(result, mock_devices)
        self.mock_db.query.assert_called_once_with(Device)

        # Check that filter was called with a condition involving the search term.
        # This requires knowledge of how the ILIKE/CONTAINS is constructed.
        # For a basic check:
        mock_query_obj.filter.assert_called_once()
        # Example of more specific check (assuming OR and ILIKE, may need adjustment based on actual service code):
        # filter_arg = mock_query_obj.filter.call_args[0][0]
        # self.assertTrue(str(filter_arg).lower().count(f"%{search_term.lower()}%") >= 2) # For name and description

        mock_filter_obj.offset.assert_called_once_with(offset_val)
        mock_offset_obj.limit.assert_called_once_with(limit_val)
        mock_limit_obj.all.assert_called_once()

    def test_search_devices_by_term_no_results(self):
        self.mock_db.query.side_effect = None
        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_limit_obj = MagicMock()
        mock_offset_obj = MagicMock()

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        mock_filter_obj.offset.return_value = mock_offset_obj
        mock_offset_obj.limit.return_value = mock_limit_obj
        mock_limit_obj.all.return_value = []

        result = self.service.search_devices_by_term("Omega", limit=5, offset=0)
        self.assertEqual(result, [])
        mock_filter_obj.offset.assert_called_once_with(0)
        mock_offset_obj.limit.assert_called_once_with(5)

    def test_get_devices_by_organization_name(self):
        self.mock_db.query.side_effect = None
        org_name = "Test Org"
        mock_devices = [Device(organization_name=org_name, identifier="d1"), Device(organization_name=org_name, identifier="d2")]

        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_limit_obj = MagicMock()
        mock_offset_obj = MagicMock()

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        mock_filter_obj.offset.return_value = mock_offset_obj
        mock_offset_obj.limit.return_value = mock_limit_obj
        mock_limit_obj.all.return_value = mock_devices

        limit_val = 20
        offset_val = 0
        result = self.service.get_devices_by_organization_name(org_name, limit=limit_val, offset=offset_val)

        self.assertEqual(result, mock_devices)
        self.mock_db.query.assert_called_once_with(Device)
        # mock_query_obj.filter.assert_called_once_with(Device.organization_name == org_name) # Requires Device.organization_name to be mockable
        mock_query_obj.filter.assert_called_once() # Basic check
        mock_filter_obj.offset.assert_called_once_with(offset_val)
        mock_offset_obj.limit.assert_called_once_with(limit_val)
        mock_limit_obj.all.assert_called_once()

    def test_get_devices_by_site_name(self):
        self.mock_db.query.side_effect = None
        site_name = "Main Site"
        mock_devices = [Device(site_name=site_name, identifier="s1"), Device(site_name=site_name, identifier="s2")]

        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_limit_obj = MagicMock()
        mock_offset_obj = MagicMock()

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        mock_filter_obj.offset.return_value = mock_offset_obj
        mock_offset_obj.limit.return_value = mock_limit_obj
        mock_limit_obj.all.return_value = mock_devices

        limit_val = 15
        offset_val = 5
        result = self.service.get_devices_by_site_name(site_name, limit=limit_val, offset=offset_val)

        self.assertEqual(result, mock_devices)
        self.mock_db.query.assert_called_once_with(Device)
        # mock_query_obj.filter.assert_called_once_with(Device.site_name == site_name)
        mock_query_obj.filter.assert_called_once() # Basic check
        mock_filter_obj.offset.assert_called_once_with(offset_val)
        mock_offset_obj.limit.assert_called_once_with(limit_val)
        mock_limit_obj.all.assert_called_once()

    def test_get_devices_with_critical_alerts(self):
        self.mock_db.query.side_effect = None
        mock_devices = [
            Device(identifier="c1", has_alerts=True, alert_severity="critical", last_alert_date=datetime.now(timezone.utc)),
            Device(identifier="c2", has_alerts=True, alert_severity="critical", last_alert_date=datetime.now(timezone.utc))
        ]

        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_orderby_obj = MagicMock()
        mock_limit_obj = MagicMock()
        mock_offset_obj = MagicMock()

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        mock_filter_obj.order_by.return_value = mock_orderby_obj
        mock_orderby_obj.offset.return_value = mock_offset_obj
        mock_offset_obj.limit.return_value = mock_limit_obj
        mock_limit_obj.all.return_value = mock_devices

        limit_val = 10
        offset_val = 0
        result = self.service.get_devices_with_critical_alerts(limit=limit_val, offset=offset_val)

        self.assertEqual(result, mock_devices)
        self.mock_db.query.assert_called_once_with(Device)
        # mock_query_obj.filter.assert_called_once_with(Device.has_alerts == True, Device.alert_severity == 'critical')
        self.assertEqual(mock_query_obj.filter.call_count, 1) # Check filter was called (specific args are harder)
        mock_filter_obj.order_by.assert_called_once() # Check order_by was called
        mock_orderby_obj.offset.assert_called_once_with(offset_val)
        mock_offset_obj.limit.assert_called_once_with(limit_val)
        mock_limit_obj.all.assert_called_once()

    def test_get_devices_with_elevated_alerts(self):
        self.mock_db.query.side_effect = None
        mock_devices = [
            Device(identifier="e1", has_alerts=True, alert_severity="elevated", last_alert_date=datetime.now(timezone.utc)),
        ]
        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_orderby_obj = MagicMock()
        mock_limit_obj = MagicMock()
        mock_offset_obj = MagicMock()

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        mock_filter_obj.order_by.return_value = mock_orderby_obj
        mock_orderby_obj.offset.return_value = mock_offset_obj
        mock_offset_obj.limit.return_value = mock_limit_obj
        mock_limit_obj.all.return_value = mock_devices

        limit_val = 5
        offset_val = 0
        result = self.service.get_devices_with_elevated_alerts(limit=limit_val, offset=offset_val)

        self.assertEqual(result, mock_devices)
        self.mock_db.query.assert_called_once_with(Device)
        # mock_query_obj.filter.assert_called_once_with(Device.has_alerts == True, Device.alert_severity == 'elevated')
        self.assertEqual(mock_query_obj.filter.call_count, 1) # Check filter was called
        mock_filter_obj.order_by.assert_called_once()
        mock_orderby_obj.offset.assert_called_once_with(offset_val)
        mock_offset_obj.limit.assert_called_once_with(limit_val)
        mock_limit_obj.all.assert_called_once()

    def test_get_offline_devices_list(self):
        self.mock_db.query.side_effect = None
        mock_devices = [
            Device(identifier="off1", is_online=False, last_seen_online=datetime.now(timezone.utc)),
            Device(identifier="off2", is_online=False, last_seen_online=datetime.now(timezone.utc))
        ]
        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()
        mock_orderby_obj = MagicMock()
        mock_limit_obj = MagicMock()
        mock_offset_obj = MagicMock()

        self.mock_db.query.return_value = mock_query_obj
        mock_query_obj.filter.return_value = mock_filter_obj
        mock_filter_obj.order_by.return_value = mock_orderby_obj
        mock_orderby_obj.offset.return_value = mock_offset_obj
        mock_offset_obj.limit.return_value = mock_limit_obj
        mock_limit_obj.all.return_value = mock_devices

        limit_val = 25
        offset_val = 0
        result = self.service.get_offline_devices_list(limit=limit_val, offset=offset_val)

        self.assertEqual(result, mock_devices)
        self.mock_db.query.assert_called_once_with(Device)
        # mock_query_obj.filter.assert_called_once_with(Device.is_online == False)
        mock_query_obj.filter.assert_called_once() # Basic check
        mock_filter_obj.order_by.assert_called_once()
        mock_orderby_obj.offset.assert_called_once_with(offset_val)
        mock_offset_obj.limit.assert_called_once_with(limit_val)
        mock_limit_obj.all.assert_called_once()

    # --- Tests for get_device_or_raise ---

    def test_get_device_or_raise_found(self):
        self.mock_db.query.side_effect = None
        device_id = "existing_device_id"
        mock_device_instance = Device(identifier=device_id, name="Found Device")

        mock_query = self.mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_device_instance

        result = self.service.get_device_or_raise(device_id)

        self.assertEqual(result, mock_device_instance)
        self.mock_db.query.assert_called_once_with(Device)
        # More specific filter check (optional, depends on complexity/need)
        # filter_arg = mock_filter.call_args[0][0]
        # self.assertEqual(str(filter_arg), str(Device.identifier == device_id))
        mock_filter.first.assert_called_once()

    def test_get_device_or_raise_not_found(self):
        self.mock_db.query.side_effect = None
        device_id = "non_existent_device_id"

        mock_query = self.mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        with self.assertRaisesRegex(ValueError, f"Device with ID {device_id} not found."):
            self.service.get_device_or_raise(device_id)

        self.mock_db.query.assert_called_once_with(Device)
        mock_filter.first.assert_called_once()

    # --- Tests for get_notifications_for_device ---

    def test_get_notifications_for_device_found(self):
        self.mock_db.query.side_effect = None # Reset side_effect
        device_id = "dev_with_notifs"
        limit_val = 10
        offset_val = 0
        mock_found_device = Device(identifier=device_id, name="DeviceForNotifs")
        mock_notifications = [Notification(id=1, device_id=device_id, message="Notif 1"), Notification(id=2, device_id=device_id, message="Notif 2")]

        # Mock setup for the two separate query chains
        # 1. For the get_device_or_raise call (simplified: assume it works by direct query mock)
        mock_device_query = MagicMock()
        mock_device_filter = MagicMock()
        mock_device_filter.first.return_value = mock_found_device

        # 2. For the notifications query
        mock_notif_query = MagicMock()
        mock_notif_filter = MagicMock()
        mock_notif_orderby = MagicMock()
        mock_notif_offset = MagicMock()
        mock_notif_limit = MagicMock()
        mock_notif_limit.all.return_value = mock_notifications

        # Use side_effect to return different mocks based on the model being queried
        def query_side_effect_for_notifs(model):
            if model == Device:
                return mock_device_query
            elif model == Notification:
                return mock_notif_query
            return MagicMock() # Should not happen in this test

        self.mock_db.query.side_effect = query_side_effect_for_notifs

        # Configure the chain for Device query (used by get_device_or_raise)
        mock_device_query.filter.return_value = mock_device_filter

        # Configure the chain for Notification query
        mock_notif_query.filter.return_value = mock_notif_filter
        mock_notif_filter.order_by.return_value = mock_notif_orderby
        mock_notif_orderby.offset.return_value = mock_notif_offset
        mock_notif_offset.limit.return_value = mock_notif_limit

        result = self.service.get_notifications_for_device(device_id, limit=limit_val, offset=offset_val)

        self.assertEqual(result, mock_notifications)

        # Assert calls for device query part
        mock_device_query.filter.assert_called_once() # Basic check on filter
        mock_device_filter.first.assert_called_once()

        # Assert calls for notification query part
        mock_notif_query.filter.assert_called_once() # Basic check
        mock_notif_filter.order_by.assert_called_once()
        mock_notif_orderby.offset.assert_called_once_with(offset_val)
        mock_notif_offset.limit.assert_called_once_with(limit_val)
        mock_notif_limit.all.assert_called_once()

        # Check that self.mock_db.query was called for Device and Notification
        self.assertIn(call(Device), self.mock_db.query.call_args_list)
        self.assertIn(call(Notification), self.mock_db.query.call_args_list)


    def test_get_notifications_for_device_no_notifications(self):
        self.mock_db.query.side_effect = None
        device_id = "dev_no_notifs"
        mock_found_device = Device(identifier=device_id, name="DeviceNoNotifs")

        mock_device_query = MagicMock()
        mock_device_filter = MagicMock()
        mock_device_filter.first.return_value = mock_found_device

        mock_notif_query = MagicMock()
        mock_notif_filter = MagicMock()
        mock_notif_orderby = MagicMock()
        mock_notif_offset = MagicMock()
        mock_notif_limit = MagicMock()
        mock_notif_limit.all.return_value = [] # No notifications

        def query_side_effect_for_no_notifs(model):
            if model == Device: return mock_device_query
            elif model == Notification: return mock_notif_query
            return MagicMock()

        self.mock_db.query.side_effect = query_side_effect_for_no_notifs
        mock_device_query.filter.return_value = mock_device_filter
        mock_notif_query.filter.return_value = mock_notif_filter
        mock_notif_filter.order_by.return_value = mock_notif_orderby
        mock_notif_orderby.offset.return_value = mock_notif_offset
        mock_notif_offset.limit.return_value = mock_notif_limit

        result = self.service.get_notifications_for_device(device_id, limit=10, offset=0)
        self.assertEqual(result, [])
        mock_notif_limit.all.assert_called_once()


    def test_get_notifications_for_device_device_not_found(self):
        self.mock_db.query.side_effect = None
        device_id = "non_existent_for_notifs"

        # Mock the query for Device to return None (simulating get_device_or_raise failure)
        mock_device_query = MagicMock()
        mock_device_filter = MagicMock()
        mock_device_filter.first.return_value = None

        # Only Device query should happen
        self.mock_db.query.return_value = mock_device_query # Simplified side_effect for this case
        mock_device_query.filter.return_value = mock_device_filter

        with self.assertRaisesRegex(ValueError, f"Device with ID {device_id} not found."):
            self.service.get_notifications_for_device(device_id, limit=10, offset=0)

        self.mock_db.query.assert_called_once_with(Device) # Ensure only device query was attempted
        mock_device_filter.first.assert_called_once()


    # --- Tests for get_assets_for_device ---

    def test_get_assets_for_device_found(self):
        self.mock_db.query.side_effect = None
        device_id = "dev_with_assets"
        mock_found_device = Device(identifier=device_id, name="DeviceForAssets")
        mock_asset = DeviceAsset(device_id=device_id, asset_type="Laptop")

        mock_device_query = MagicMock()
        mock_device_filter = MagicMock()
        mock_device_filter.first.return_value = mock_found_device # For get_device_or_raise

        mock_asset_query = MagicMock()
        mock_asset_filter = MagicMock()
        mock_asset_filter.first.return_value = mock_asset # For asset query

        def query_side_effect_for_assets(model):
            if model == Device: return mock_device_query
            elif model == DeviceAsset: return mock_asset_query
            return MagicMock()

        self.mock_db.query.side_effect = query_side_effect_for_assets
        mock_device_query.filter.return_value = mock_device_filter
        mock_asset_query.filter.return_value = mock_asset_filter

        result = self.service.get_assets_for_device(device_id)
        self.assertEqual(result, mock_asset)

        # Assert calls for device query part
        mock_device_query.filter.assert_called_once()
        mock_device_filter.first.assert_called_once()

        # Assert calls for asset query part
        mock_asset_query.filter.assert_called_once() # Basic check
        mock_asset_filter.first.assert_called_once()

        self.assertIn(call(Device), self.mock_db.query.call_args_list)
        self.assertIn(call(DeviceAsset), self.mock_db.query.call_args_list)

    def test_get_assets_for_device_no_assets_found(self):
        self.mock_db.query.side_effect = None
        device_id = "dev_no_assets"
        mock_found_device = Device(identifier=device_id, name="DeviceNoAssets")

        mock_device_query = MagicMock()
        mock_device_filter = MagicMock()
        mock_device_filter.first.return_value = mock_found_device

        mock_asset_query = MagicMock()
        mock_asset_filter = MagicMock()
        mock_asset_filter.first.return_value = None # No assets found

        def query_side_effect_no_assets(model):
            if model == Device: return mock_device_query
            elif model == DeviceAsset: return mock_asset_query
            return MagicMock()

        self.mock_db.query.side_effect = query_side_effect_no_assets
        mock_device_query.filter.return_value = mock_device_filter
        mock_asset_query.filter.return_value = mock_asset_filter

        with self.assertRaisesRegex(ValueError, f"Assets not found for device ID {device_id}."):
            self.service.get_assets_for_device(device_id)

        mock_asset_filter.first.assert_called_once()


    def test_get_assets_for_device_device_not_found(self):
        self.mock_db.query.side_effect = None
        device_id = "non_existent_for_assets"

        mock_device_query = MagicMock()
        mock_device_filter = MagicMock()
        mock_device_filter.first.return_value = None # Device not found by get_device_or_raise

        self.mock_db.query.return_value = mock_device_query # Simplified side_effect
        mock_device_query.filter.return_value = mock_device_filter

        mock_asset_query = self.mock_db.query(DeviceAsset) # Ensure this doesn't get called

        with self.assertRaisesRegex(ValueError, f"Device with ID {device_id} not found."):
            self.service.get_assets_for_device(device_id)

        self.mock_db.query.assert_called_once_with(Device) # Only device query should happen
        mock_asset_query.assert_not_called()


if __name__ == '__main__':
    unittest.main()
