coverage erase

### common/secretモジュール単体テスト

# T01
coverage run -a -m tests.common.secret.T01_SecretStore_01_store_test
coverage run -a -m tests.common.secret.T01_SecretStore_02_store_edge_test
coverage run -a -m tests.common.secret.T01_SecretStore_03_store_init_test
coverage run -a -m tests.common.secret.T01_SecretStore_04_store_misc_test
coverage run -a -m tests.common.secret.T01_SecretStore_05impl_store_misc_test

# ## common/chatモジュール単体テスト

# # T01 : common/chat/provider.py
# coverage run -a -m tests.common.chat._T01_Provider_01_provider_test
# # T02 : common/chat/auth.py
# $env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
# coverage run -a -m tests.common.chat._T02_Auth_01_auth_resolve_test
# Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE
# # T03 : common/chat/chat_core.py
# coverage run -a -m tests.common.chat._T03_ChatCore_01_chat_core_test
# # T04 : common/chat/chat_loop.py
# coverage run -a -m tests.common.chat._T04_ChatLoop_01_chat_loop_test
# coverage run -a -m tests.common.chat._T04_ChatLoop_02_chat_loop_edges_test
# coverage run -a -m tests.common.chat._T04_ChatLoop_03_chat_loop_more_edges_test
# coverage run -a -m tests.common.chat._T04_ChatLoop_04_chat_loop_cover_rest_test
# coverage run -a -m tests.common.chat._T04_ChatLoop_05_chat_loop_helper_paths_test
# coverage run -a -m tests.common.chat.T04_ChatLoop_06-impl_chat_loop_paths_cover_test
# coverage run -a -m tests.common.chat.T04_ChatLoop_07-impl_chat_loop_helpers_test
# # T05 : common/chat/message.py
# coverage run -a -m tests.common.chat._T05_Message_01_message_test
# # T06 : common/chat/textsplit.py
# coverage run -a -m tests.common.chat._T06_TextSplit_01_textsplit_test
# coverage run -a -m tests.common.chat._T06_TextSplit_02_textsplit_edges_test
# coverage run -a -m tests.common.chat._T06_TextSplit_03_textsplit_more_cases_test
# coverage run -a -m tests.common.chat.T06_TextSplit_04-impl_textsplit_arg_compat_test
# # T07 : common/chat/continuation.py
# coverage run -a -m tests.common.chat._T07_Continuation_01_continuation_test
# coverage run -a -m tests.common.chat._T07_Continuation_02_continuation_edges_test
# coverage run -a -m tests.common.chat.T07_Continuation_03-impl_continuation_guards_test
# coverage run -a -m tests.common.chat.T07_Continuation_04-impl_continuation_guards2_test
# coverage run -a -m tests.common.chat.T07_Continuation_05-impl_continuation_tail_and_prepare_test
# coverage run -a -m tests.common.chat.T07_Continuation_06-impl_continuation_top_level_guards_test

# ### common/utilsモジュール単体テスト

# # T01 : common/utils/redact.py
# coverage run -a -m tests.common.utils.T01_Redact_01_redact_test
# # T02 : common/utils/logger.py
# coverage run -a -m tests.common.utils.T02_Logger_01_logger_test
# # T03 : common/utils/jsonc.py
# coverage run -a -m tests.common.utils.T03_Jsonc_01_jsonc_test
# # T04 : common/utils/file_io.py
# coverage run -a -m tests.common.utils.T04_FileIo_01_file_io_test
# # T05 : common/utils/attachments.py
# coverage run -a -m tests.common.utils.T05_Attachments_01_attachments_test
# # T06 : common/utils/prefetch.py
# coverage run -a -m tests.common.utils.T06_Prefetch_01_prefetch_test
# # T07 : common/utils/thread_utils.py
# coverage run -a -m tests.common.utils.T07_ThreadUtils_01_thread_utils_test
# coverage run -a -m tests.common.utils.T07_ThreadUtils_02_thread_utils_branch_test
# # T08 : common/utils/webread_utils.py
# coverage run -a -m tests.common.utils.T08_WebReadUtils_01_webread_utils_test
# coverage run -a -m tests.common.utils.T08_WebReadUtils_02_webread_utils_branch_test
# coverage run -a -m tests.common.utils.T08_WebReadUtils_03_webread_utils_remaining_branch_test
# coverage run -a -m tests.common.utils.T08_WebReadUtils_04_webread_utils_more_branch_test
# coverage run -a -m tests.common.utils.T08_WebReadUtils_05_webread_utils_last_branch_test

# ### common/sessionモジュール単体テスト

# # T01 : common/session/user_session_manager.py
# coverage run -a -m tests.common.session.T01_UserSession_01_user_session_test
# # T02 : common/session/server_session_manager.py
# coverage run -a -m tests.common.session.T02_ServerSession_01_server_session_test
# coverage run -a -m tests.common.session.T02_ServerSession_02_server_session_branch_test
# # T03 : common/session/thread_context_manager.py
# coverage run -a -m tests.common.session.T03_ThreadContext_01_thread_context_test

coverage report -m
# coverage html
# htmlcov/index.html
