cls
coverage erase
# coverage run -a -m tests.T01_Provider_01_provider_test
# coverage run -a -m tests.T02_SecretStore_01_store_test
# coverage run -a -m tests.T02_SecretStore_02_store_edge_test
# coverage run -a -m tests.T02_SecretStore_03_store_init_test
# coverage run -a -m tests.T02_SecretStore_04_store_misc_test
# $env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
# coverage run -a -m tests.T03_Auth_01_auth_resolve_test
# Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE
# coverage run -a -m tests.T04_ChatCore_01_chat_core_test
# coverage run -a -m tests.T05_ChatLoop_01_chat_loop_test
# coverage run -a -m tests.T05_ChatLoop_02_chat_loop_edges_test
# coverage run -a -m tests.T05_ChatLoop_03_chat_loop_more_edges_test
# coverage run -a -m tests.T05_ChatLoop_04_chat_loop_cover_rest_test
# coverage run -a -m tests.T05_ChatLoop_05_chat_loop_helper_paths_test
# coverage run -a -m tests.T05_ChatLoop_06_chat_loop_paths_cover_test
# coverage run -a -m tests.T05_ChatLoop_07_chat_loop_helpers_test
coverage run -a -m tests.T06_Message_01_message_test
# coverage run -a -m tests.T07_Context_01_context_test
coverage report -m
coverage html
htmlcov/index.html
