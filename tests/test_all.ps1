coverage erase

### M01: common/secretモジュール単体テスト

# T01
coverage run -a -m tests.common.secret.T01_SecretStore_01_store_test
coverage run -a -m tests.common.secret.T01_SecretStore_02_store_edge_test
coverage run -a -m tests.common.secret.T01_SecretStore_03_store_init_test
coverage run -a -m tests.common.secret.T01_SecretStore_04_store_misc_test

### M02: common/chatモジュール単体テスト

# T01 : common/chat/provider.py
coverage run -a -m tests.common.chat.T01_Provider_01_provider_test

# # T03
# $env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
# coverage run -a -m tests.common.chat.T03_Auth_01_auth_resolve_test
# Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE

# # T04
# coverage run -a -m tests.common.chat.T04_ChatCore_01_chat_core_test

# # T05
# coverage run -a -m tests.common.chat.T05_ChatLoop_01_chat_loop_test
# coverage run -a -m tests.common.chat.T05_ChatLoop_02_chat_loop_edges_test
# coverage run -a -m tests.common.chat.T05_ChatLoop_03_chat_loop_more_edges_test
# coverage run -a -m tests.common.chat.T05_ChatLoop_04_chat_loop_cover_rest_test
# coverage run -a -m tests.common.chat.T05_ChatLoop_05_chat_loop_helper_paths_test
# coverage run -a -m tests.common.chat.T05_ChatLoop_06_chat_loop_paths_cover_test
# coverage run -a -m tests.common.chat.T05_ChatLoop_07_chat_loop_helpers_test

# # T06
# coverage run -a -m tests.common.chat.T06_Message_01_message_test


# T07
# coverage run -a -m tests.common.chat.T07_Context_01_context_test

coverage report -m
coverage html
htmlcov/index.html
