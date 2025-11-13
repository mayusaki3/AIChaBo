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

# T02 : common/chat/auth.py
$env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
coverage run -a -m tests.common.chat.T02_Auth_01_auth_resolve_test
Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE

# T03 : common/chat/chat_core.py
coverage run -a -m tests.common.chat.T03_ChatCore_01_chat_core_test

# T04 : common/chat/chat_loop.py
coverage run -a -m tests.common.chat.T04_ChatLoop_01_chat_loop_test
coverage run -a -m tests.common.chat.T04_ChatLoop_02_chat_loop_edges_test
coverage run -a -m tests.common.chat.T04_ChatLoop_03_chat_loop_more_edges_test
coverage run -a -m tests.common.chat.T04_ChatLoop_04_chat_loop_cover_rest_test
coverage run -a -m tests.common.chat.T04_ChatLoop_05_chat_loop_helper_paths_test
coverage run -a -m tests.common.chat.T04_ChatLoop_06_chat_loop_paths_cover_test
coverage run -a -m tests.common.chat.T04_ChatLoop_07_chat_loop_helpers_test

# T05 : common/chat/message.py
coverage run -a -m tests.common.chat.T05_Message_01_message_test

# T06 : common/chat/
# coverage run -a -m tests.common.chat.T06_Context_01_context_test

coverage report -m
coverage html
htmlcov/index.html
