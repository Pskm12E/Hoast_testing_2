#!/usr/bin/env bash
# One-time administrator setup. Only the fixed Notebook command becomes passwordless.
set -Eeuo pipefail
umask 077
[[ $EUID == 0 && $(hostname) == 4bytedigi ]]
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
rule=/etc/sudoers.d/notebook-deploy
[[ ! -e "$rule" && ! -e /usr/local/lib/notebook-deploy && ! -e /usr/local/sbin/notebook-deploy ]]
id pyie >/dev/null
visudo -c
install -d -m 755 -o root -g root /usr/local/lib/notebook-deploy
install -m 644 -o root -g root "$source_dir/install.py" /usr/local/lib/notebook-deploy/install.py
install -m 644 -o root -g root "$source_dir/passwordless-entry.py" /usr/local/lib/notebook-deploy/entry.py
install -m 755 -o root -g root "$source_dir/notebook-deploy" /usr/local/sbin/notebook-deploy
python3 -I -m py_compile /usr/local/lib/notebook-deploy/install.py /usr/local/lib/notebook-deploy/entry.py
temporary=$(mktemp /etc/sudoers.d/.notebook-deploy.XXXXXXXX)
trap 'rm -f -- "$temporary"' EXIT
printf '%s\n' '# Only the root-owned Notebook asset deployment command, with no arguments.' \
    'pyie ALL=(root) NOPASSWD: /usr/local/sbin/notebook-deploy ""' > "$temporary"
chmod 440 "$temporary"
visudo -cf "$temporary"
mv -- "$temporary" "$rule"
if ! visudo -c; then
    mv -- "$rule" /root/notebook-deploy-sudoers.rejected
    exit 1
fi
printf 'NOTEBOOK_PASSWORDLESS_DEPLOYMENT_READY\n'
