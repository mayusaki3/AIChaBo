
param(
    [string]$Filter = ""
)

# --- UTF-8 蜃ｺ蜉帙ｒ蠑ｷ蛻ｶ・域枚蟄怜喧縺大ｯｾ遲厄ｼ・---
try {
    # PowerShell / Console 縺ｮ蜃ｺ蜉帙お繝ｳ繧ｳ繝ｼ繝・ぅ繝ｳ繧ｰ繧・UTF-8 縺ｫ謠・∴繧・
    $utf8 = [System.Text.UTF8Encoding]::new($false) # BOM縺ｪ縺・
    [Console]::OutputEncoding = $utf8
    $OutputEncoding = $utf8

    # Python 縺ｮ讓呎ｺ門・蜃ｺ蜉帙ｒ UTF-8 縺ｫ蟇・○繧具ｼ・indows縺ｧ繧ょｮ牙ｮ夲ｼ・
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
} catch {
    # 螟ｱ謨励＠縺ｦ繧ゅユ繧ｹ繝亥ｮ溯｡後・邯咏ｶ・
}

# 螳溯｡悟ｯｾ雎｡繝・せ繝井ｸ隕ｧ
$Tests = @(
    ### common/secret繝｢繧ｸ繝･繝ｼ繝ｫ蜊倅ｽ薙ユ繧ｹ繝・

    # T01
    "tests.common.secret.T01_SecretStore_01_store_test",
    "tests.common.secret.T01_SecretStore_02_store_edge_test",
    "tests.common.secret.T01_SecretStore_03_store_init_test",
    "tests.common.secret.T01_SecretStore_04_store_misc_test",
    "tests.common.secret.T01_SecretStore_05impl_store_misc_test",

    ### common/session繝｢繧ｸ繝･繝ｼ繝ｫ蜊倅ｽ薙ユ繧ｹ繝・

    # T01 : common/session/user_session_manager.py
    "tests.common.session.T01_user_session_01_user_session_test",
    "tests.common.session.T01_user_session_02impl_user_session_test",

    # T02 : common/session/server_session_manager.py
    # tests.common.session.T02_ServerSession_01_server_session_test
    # tests.common.session.T02_ServerSession_02_server_session_branch_test

# T03 : common/session/thread_context_manager.py
#tests.common.session.T03_ThreadContext_01_thread_context_test


# ## common/chat繝｢繧ｸ繝･繝ｼ繝ｫ蜊倅ｽ薙ユ繧ｹ繝・

# # T01 : common/chat/provider.py
#tests.common.chat._T01_Provider_01_provider_test
# # T02 : common/chat/auth.py
# $env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE=1
#tests.common.chat._T02_Auth_01_auth_resolve_test
# Remove-Item Env:AIChaBo_TEST_ENABLE_AUTH_RESOLVE
# # T03 : common/chat/chat_core.py
#tests.common.chat._T03_ChatCore_01_chat_core_test
# # T04 : common/chat/chat_loop.py
#tests.common.chat._T04_ChatLoop_01_chat_loop_test
#tests.common.chat._T04_ChatLoop_02_chat_loop_edges_test
#tests.common.chat._T04_ChatLoop_03_chat_loop_more_edges_test
#tests.common.chat._T04_ChatLoop_04_chat_loop_cover_rest_test
#tests.common.chat._T04_ChatLoop_05_chat_loop_helper_paths_test
#tests.common.chat.T04_ChatLoop_06-impl_chat_loop_paths_cover_test
#tests.common.chat.T04_ChatLoop_07-impl_chat_loop_helpers_test
# # T05 : common/chat/message.py
#tests.common.chat._T05_Message_01_message_test
# # T06 : common/chat/textsplit.py
#tests.common.chat._T06_TextSplit_01_textsplit_test
#tests.common.chat._T06_TextSplit_02_textsplit_edges_test
#tests.common.chat._T06_TextSplit_03_textsplit_more_cases_test
#tests.common.chat.T06_TextSplit_04-impl_textsplit_arg_compat_test
# # T07 : common/chat/continuation.py
#tests.common.chat._T07_Continuation_01_continuation_test
#tests.common.chat._T07_Continuation_02_continuation_edges_test
#tests.common.chat.T07_Continuation_03-impl_continuation_guards_test
#tests.common.chat.T07_Continuation_04-impl_continuation_guards2_test
#tests.common.chat.T07_Continuation_05-impl_continuation_tail_and_prepare_test
#tests.common.chat.T07_Continuation_06-impl_continuation_top_level_guards_test

# ### common/utils繝｢繧ｸ繝･繝ｼ繝ｫ蜊倅ｽ薙ユ繧ｹ繝・

# # T01 : common/utils/redact.py
#tests.common.utils.T01_Redact_01_redact_test
# # T02 : common/utils/logger.py
#tests.common.utils.T02_Logger_01_logger_test
# # T03 : common/utils/jsonc.py
#tests.common.utils.T03_Jsonc_01_jsonc_test
# # T04 : common/utils/file_io.py
#tests.common.utils.T04_FileIo_01_file_io_test
# # T05 : common/utils/attachments.py
#tests.common.utils.T05_Attachments_01_attachments_test
# # T06 : common/utils/prefetch.py
#tests.common.utils.T06_Prefetch_01_prefetch_test
# # T07 : common/utils/thread_utils.py
#tests.common.utils.T07_ThreadUtils_01_thread_utils_test
#tests.common.utils.T07_ThreadUtils_02_thread_utils_branch_test
# # T08 : common/utils/webread_utils.py
#tests.common.utils.T08_WebReadUtils_01_webread_utils_test
#tests.common.utils.T08_WebReadUtils_02_webread_utils_branch_test
#tests.common.utils.T08_WebReadUtils_03_webread_utils_remaining_branch_test
#tests.common.utils.T08_WebReadUtils_04_webread_utils_more_branch_test
#tests.common.utils.T08_WebReadUtils_05_webread_utils_last_branch_test



    ""
)

if ($Filter -eq "?") {
    Write-Error "繝・せ繝医さ繝槭Φ繝我ｸ隕ｧ:"
    foreach ($test in $Tests) {
        if ($Test -ne "") {
            Write-Host "> python -X utf8 -m coverage run -a -m $test"
        }
    }
    exit 1
}

# 繝輔ぅ繝ｫ繧ｿ驕ｩ逕ｨ
if ($Filter -ne "") {
    $Tests = $Tests | Where-Object { $_ -like "$Filter*" }
}

if ($Tests.Count -eq 0) {
    Write-Error "隧ｲ蠖薙☆繧九ユ繧ｹ繝医′縺ゅｊ縺ｾ縺帙ｓ: $Filter"
    exit 1
}

python -X utf8 -m coverage erase

foreach ($test in $Tests) {
    if ($Test -ne "") {
        python -X utf8 -m coverage run -a -m $test
    }
}

python -X utf8 -m coverage report -m
# python -X utf8 -m coverage html
# htmlcov/index.html

