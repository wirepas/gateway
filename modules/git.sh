##
## @brief      Retrives and stores git build information
##
function git_commit_info
{
    rm build-*.txt || true
    LAST_HASH=$(git log -n 1 --oneline --format=%H)
    git log -n 10 --oneline > build-${LAST_HASH}.txt
}


##
## @brief      Clones a given git repository
##
function git_clone_repo
{
   REPO_NAME=${1}
   REPO_DIR=${2:-"${REPO_NAME}"}
   rm -rf ${REPO_DIR}
   git clone ssh://git@github.com/wirepas/${REPO_NAME} ${REPO_DIR}

}

