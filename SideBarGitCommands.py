# coding=utf8

import sublime_plugin
import sublime
import os
import re
import threading


from .SideBarAPI import SideBarSelection
from .SideBarAPI import SideBarItem
from .SideBarGit import SideBarGit


class Object:
    pass


class WriteToViewCommand(sublime_plugin.TextCommand):
    def run(self, edit, content):
        content = content.split("\n")
        for k, v in enumerate(content):
            index = v[:3]
            if index == "+++":
                content[k] = content[k] + "\n"
            elif index == "---":
                content[k] = "\n" + content[k]
            else:
                content[k] = "\t" + v
        content = "\n".join(content)
        view = self.view
        view.replace(edit, sublime.Region(0, view.size()), content)
        view.sel().clear()
        view.sel().add(sublime.Region(0))
        view.end_edit(edit)


# run last command again on a focused tab when pressing F5


class SideBarGitRefreshTabContentsByRunningCommandAgain(sublime_plugin.WindowCommand):
    def run(self):
        window = sublime.active_window()
        if not window:
            return
        view = window.active_view()
        if view is None:
            return
        if view.settings().has("SideBarGitIsASideBarGitTab"):
            SideBarGit().run(
                [],
                view.settings().get("SideBarGitModal"),
                view.settings().get("SideBarGitBackground"),
                view,
                view.settings().get("SideBarGitCommand"),
                view.settings().get("SideBarGitItem"),
                view.settings().get("SideBarGitToStatusBar"),
                view.settings().get("SideBarGitTitle"),
                view.settings().get("SideBarGitNoResults"),
                view.settings().get("SideBarGitSyntaxFile"),
            )
        elif view.file_name():
            view.run_command("revert")

    def is_enabled(self):
        window = sublime.active_window()
        if not window:
            return False
        view = window.active_view()
        if view is None:
            return False
        if view.settings().has("SideBarGitIsASideBarGitTab") or view.file_name():
            return True
        return False


def closed_affected_items(items):
    closed_items = []
    for item in items:
        if not item.isDirectory():
            closed_items += item.closeViews()
    return closed_items


def reopen_affected_items(closed_items, active):
    active_view = sublime.active_window().active_view()

    for item in closed_items:
        file_name, window, view_index = item
        if window and os.path.exists(file_name):
            view = window.open_file(file_name)
            window.set_view_index(view, view_index[0], view_index[1])
            if file_name == active:
                active_view = view
    sublime.active_window().focus_view(active_view)


# commands


class sidebar_git_add(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for repo in SideBarGit().getSelectedRepos(
            SideBarSelection(paths).getSelectedItems()
        ):
            command = ["git", "add", "--"]
            for item in repo.items:
                command.append(
                    item.forCwdSystemPathRelativeFromRecursive(repo.repository.path())
                )
            object = Object()
            object.item = repo.repository
            object.command = command
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_add_commit(sublime_plugin.WindowCommand):
    def run(self, paths=[], input=False, content=""):
        if input is False:
            SideBarGit().prompt("Message: ", "", self.run, paths)
            sublime.active_window().run_command(
                "toggle_setting", {"setting": "spell_check"}
            )
        elif content != "":
            content = content[0].upper() + content[1:]
            for repo in SideBarGit().getSelectedRepos(
                SideBarSelection(paths).getSelectedItems()
            ):
                commitCommandAdd = ["git", "add", "--"]
                commitCommandCommit = ["git", "commit", "-m", content, "--"]
                for item in repo.items:
                    commitCommandAdd.append(
                        item.forCwdSystemPathRelativeFromRecursive(
                            repo.repository.path()
                        )
                    )
                    commitCommandCommit.append(
                        item.forCwdSystemPathRelativeFrom(repo.repository.path())
                    )
                object = Object()
                object.item = repo.repository
                object.command = commitCommandAdd
                SideBarGit().run(object)
                object = Object()
                object.item = repo.repository
                object.to_status_bar = True
                object.command = commitCommandCommit
                SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_commit(sublime_plugin.WindowCommand):
    def run(self, paths=[], input=False, content=""):
        if input is False:
            SideBarGit().prompt("Message: ", "", self.run, paths)
            sublime.active_window().run_command(
                "toggle_setting", {"setting": "spell_check"}
            )
        elif content != "":
            for repo in SideBarGit().getSelectedRepos(
                SideBarSelection(paths).getSelectedItems()
            ):
                commitCommand = ["git", "commit", "-m", content, "--"]
                for item in repo.items:
                    commitCommand.append(
                        item.forCwdSystemPathRelativeFrom(repo.repository.path())
                    )
                object = Object()
                object.item = repo.repository
                object.to_status_bar = True
                object.command = commitCommand
                SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_commit_amend(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for repo in SideBarGit().getSelectedRepos(
            SideBarSelection(paths).getSelectedItems()
        ):
            commitCommand = ["git", "commit", "--amend", "-C", "HEAD", "--"]
            for item in repo.items:
                commitCommand.append(
                    item.forCwdSystemPathRelativeFrom(repo.repository.path())
                )
            object = Object()
            object.item = repo.repository
            object.to_status_bar = True
            object.command = commitCommand
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_commit_undo(sublime_plugin.WindowCommand):
    def run(self, paths=[], confirm=False, drop_me=""):
        if confirm is False:
            SideBarGit().confirm("Undo Commit? ", self.run, paths)
        else:
            for item in SideBarGit().getSelectedRepos(
                SideBarSelection(paths).getSelectedItems()
            ):
                object = Object()
                object.item = item.repository
                object.command = ["git", "reset", "--soft", "HEAD^"]
                SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_status(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedItems():
            object = Object()
            object.item = item
            object.command = ["git", "status", "--", item.forCwdSystemName()]
            object.title = "Status: " + item.name()
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_diff_ignore_whitespace(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedItems():
            object = Object()
            object.item = item
            object.command = [
                "git",
                "diff",
                "HEAD",
                "--no-color",
                "-w",
                "--",
                item.forCwdSystemName(),
            ]
            object.title = "Diff: " + item.name() + ".diff"
            object.no_results = "No differences to show"
            object.syntax_file = "Packages/SideBarGit/SideBarGitDiff.sublime-syntax"
            object.word_wrap = False
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_diff(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedItems():
            object = Object()
            object.item = item
            object.command = [
                "git",
                "diff",
                "HEAD",
                "--no-color",
                "--",
                item.forCwdSystemName(),
            ]
            object.title = "Diff: " + item.name() + ".diff"
            object.no_results = "No differences to show"
            object.syntax_file = "Packages/SideBarGit/SideBarGitDiff.sublime-syntax"
            object.word_wrap = False
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_diff_last50(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedItems():
            object = Object()
            object.item = item
            object.command = [
                "git",
                "log",
                "-n",
                "50",
                "-p",
                "--decorate",
                "--no-color",
                "--",
                item.forCwdSystemName(),
            ]
            object.title = "Log: " + item.name()
            object.no_results = "No log to show"
            object.syntax_file = "Packages/SideBarGit/SideBarGitDiff.sublime-syntax"
            object.word_wrap = False
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_log(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedItems():
            object = Object()
            object.item = item
            object.command = [
                "git",
                "log",
                "-n",
                "1000",
                "--pretty=format:%h% %<(10,trunc) %an%  %ad%  %s",
                "--date=short",
                "--decorate",
                "--graph",
                "--no-color",
                "--",
                item.forCwdSystemName(),
            ]
            object.title = "Log: " + item.name()
            object.no_results = "No log to show"
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_log_long(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedItems():
            object = Object()
            object.item = item
            object.command = [
                "git",
                "log",
                "-n",
                "1000",
                "--stat",
                "--decorate",
                "--graph",
                "--no-color",
                "--",
                item.forCwdSystemName(),
            ]
            object.title = "Log: " + item.name()
            object.no_results = "No log to show"
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_revert(sublime_plugin.WindowCommand):
    def run(self, paths=[], confirm=False, drop_me=""):
        failed = False
        if confirm == False:
            SideBarGit().confirm(
                "Discard changes to tracked and clean untracked on selected items? ",
                self.run,
                paths,
            )
        else:
            for item in SideBarSelection(paths).getSelectedItems():
                object = Object()
                object.item = item
                object.command = [
                    "git",
                    "checkout",
                    "HEAD",
                    "--",
                    item.forCwdSystemName(),
                ]
                if not SideBarGit().run(object):
                    failed = True
                object = Object()
                object.item = item
                object.command = [
                    "git",
                    "clean",
                    "-f",
                    "-d",
                    "--",
                    item.forCwdSystemName(),
                ]
                if not SideBarGit().run(object):
                    failed = True
            if not failed:
                SideBarGit().status(
                    "Discarded changes to tracked and cleaned untracked on selected items"
                )

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_checkout_to(sublime_plugin.WindowCommand):
    def run(self, paths=[], input=False, content=""):
        failed = False
        if input == False:
            SideBarGit().prompt(
                "Checkout selected items to object: ", "", self.run, paths
            )
        elif content != "":
            for item in SideBarSelection(paths).getSelectedItems():
                object = Object()
                object.item = item
                object.command = [
                    "git",
                    "checkout",
                    content,
                    "--",
                    item.forCwdSystemName(),
                ]
                if not SideBarGit().run(object):
                    failed = True
            if not failed:
                SideBarGit().status('Checkout selected items to "' + content + '"')

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_checkout_repo_to(sublime_plugin.WindowCommand):
    def run(self, paths=[], input=False, content=""):
        failed = False
        if input == False:
            SideBarGit().prompt("Checkout repository to object: ", "", self.run, paths)
        elif content != "":
            for item in SideBarGit().getSelectedRepos(
                SideBarSelection(paths).getSelectedItems()
            ):
                object = Object()
                object.item = item.repository
                object.command = ["git", "checkout", content]
                if not SideBarGit().run(object):
                    failed = True
            if not failed:
                SideBarGit().status('Checkout repository to "' + content + '"')

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_ignore(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedItems():
            original = item.path()
            originalIsDirectory = item.isDirectory()
            item.path(item.dirname())
            while not os.path.exists(item.join(".git")):
                if os.path.exists(item.join(".gitignore")):
                    break
                if item.dirname() == item.path():
                    break
                item.path(item.dirname())

            if os.path.exists(item.join(".gitignore")):
                item.path(item.join(".gitignore"))
            else:
                if os.path.exists(item.join(".git")):
                    item.path(item.join(".gitignore"))
                    item.create()
                else:
                    SideBarGit().status(
                        'Unable to found repository for "' + original + '"'
                    )
                    continue
            ignore_entry = re.sub(
                "^/+", "", original.replace(item.dirname(), "").replace("\\", "/")
            )

            content = item.contentUTF8().strip() + "\n" + ignore_entry
            content = content.replace("\r\n", "\n")

            item.write(content.strip())
            SideBarGit().status('Ignored file "' + ignore_entry + '" on ' + item.path())

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_init(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames():
            object = Object()
            object.item = item
            object.command = ["git", "init"]
            object.to_status_bar = True
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_clone(sublime_plugin.WindowCommand):
    def run(self, paths=[], input=False, content=""):
        failed = False
        if input == False:
            url = sublime.get_clipboard().strip()
            if ".git" not in url:
                url = ""
            SideBarGit().prompt("Enter URL to clone: ", url, self.run, paths)
        elif content != "":
            for item in SideBarSelection(paths).getSelectedDirectoriesOrDirnames():
                object = Object()
                object.item = item
                object.command = ["git", "clone", "--recursive", content]
                object.to_status_bar = True
                if not SideBarGit().run(object, True):
                    failed = True
            if not failed:
                SideBarGit().status('Cloned URL "' + content + '"')

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_push(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for item in SideBarGit().getSelectedRepos(
            SideBarSelection(paths).getSelectedItems()
        ):
            object = Object()
            object.item = item.repository
            object.command = ["git", "push", "--all"]
            object.to_status_bar = True
            SideBarGit().run(object, modal=False, background=False)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_pull(sublime_plugin.WindowCommand):
    def run(self, paths=[], confirm=False, drop_me=""):
        for item in SideBarGit().getSelectedRepos(
            SideBarSelection(paths).getSelectedItems()
        ):
            object = Object()
            object.item = item.repository
            object.command = ["git", "pull"]
            SideBarGit().run(object, True)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_remove(sublime_plugin.WindowCommand):
    def run(self, paths=[], confirm=False, drop_me=""):
        if confirm == False:
            SideBarGit().confirm(
                "Remove from repository, keep local copies? ", self.run, paths
            )
        else:
            for repo in SideBarGit().getSelectedRepos(
                SideBarSelection(paths).getSelectedItems()
            ):
                command = ["git", "rm", "-r", "--cached", "--"]
                for item in repo.items:
                    command.append(
                        item.forCwdSystemPathRelativeFrom(repo.repository.path())
                    )
                object = Object()
                object.item = repo.repository
                object.command = command
                object.to_status_bar = True
                SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_rename(sublime_plugin.WindowCommand):
    def run(self, paths=[], input=False, content=""):
        failed = False
        repo = SideBarGit().getSelectedRepos(
            SideBarSelection(paths).getSelectedItems()
        )[0]
        path = repo.items[0].forCwdSystemPathRelativeFrom(repo.repository.path())
        if input == False:
            SideBarGit().prompt("Move To: ", path, self.run, paths)
        elif content != "":
            for item in SideBarSelection(paths).getSelectedItems():
                destination = repo.repository.path() + "/" + content

                SideBarItem(destination, os.path.isdir(destination)).dirnameCreate()
                object = Object()
                object.item = SideBarItem(
                    repo.repository.path(), os.path.isdir(repo.repository.path())
                )
                object.command = ["git", "mv", path, content]
                object.to_status_bar = True
                if not SideBarGit().run(object, True):
                    failed = True
            if not failed:
                SideBarGit().status('Moved to "' + content + '"')

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() == 1


class sidebar_git_remote_add(sublime_plugin.WindowCommand):
    def run(self, paths=[], input=False, content=""):
        if input == False:
            SideBarGit().prompt(
                "Remote Add:",
                "git remote add origin " + sublime.get_clipboard().strip(),
                self.run,
                paths,
            )
        elif content != "":
            content = content
            for repo in SideBarGit().getSelectedRepos(
                SideBarSelection(paths).getSelectedItems()
            ):
                object = Object()
                object.item = repo.repository
                object.command = content.split()
                object.to_status_bar = True
                SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_branch_new(sublime_plugin.WindowCommand):
    def run(self, paths=[]):

        def create(bla1, bla2, branchName):
            branchName = branchName.strip().replace(" ", "-")

            for repo in SideBarGit().getSelectedRepos(
                SideBarSelection(paths).getSelectedItems()
            ):
                object = Object()
                object.item = repo.repository
                object.command = ["git", "branch", "-v"]
                object.silent = True
                SideBarGit().run(object, blocking=True)

                def on_done(extra, data, result):
                    result = data[result].strip()
                    if not result.startswith("*"):
                        branch = result.split(" ")[0]
                        object = Object()
                        object.item = extra
                        object.command = ["git", "checkout", branch]
                        object.to_status_bar = True
                        SideBarGit().run(object, blocking=True)

                    object = Object()
                    object.item = extra
                    object.command = ["git", "pull"]
                    object.to_status_bar = True
                    SideBarGit().run(object, blocking=True)

                    object = Object()
                    object.item = extra
                    object.command = ["git", "checkout", "-b", branchName]
                    object.to_status_bar = True
                    SideBarGit().run(object, blocking=True)

                SideBarGit().quickPanel(
                    on_done,
                    repo.repository,
                    (SideBarGit.last_stdout).split("\n"),
                )

        SideBarGit().prompt("Branch: ", "", create, "")

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_branch_switch_to(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for repo in SideBarGit().getSelectedRepos(
            SideBarSelection(paths).getSelectedItems()
        ):
            object = Object()
            object.item = repo.repository
            object.command = ["git", "branch", "-v"]
            object.silent = True
            SideBarGit().run(object, blocking=True)
            SideBarGit().quickPanel(
                self.on_done, repo.repository, (SideBarGit.last_stdout).split("\n")
            )

    def on_done(self, extra, data, result):
        result = data[result].strip()
        if result.startswith("*"):
            return
        else:
            branch = result.split(" ")[0]
            object = Object()
            object.item = extra
            object.command = ["git", "checkout", branch]
            object.to_status_bar = True
            SideBarGit().run(object, blocking=True)
            object = Object()
            object.item = extra
            object.command = ["git", "pull"]
            object.to_status_bar = True
            SideBarGit().run(object, blocking=True)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_branch_delete(sublime_plugin.WindowCommand):
    def run(self, paths=[]):
        for repo in SideBarGit().getSelectedRepos(
            SideBarSelection(paths).getSelectedItems()
        ):
            object = Object()
            object.item = repo.repository
            object.command = ["git", "branch", "-v"]
            object.silent = True
            SideBarGit().run(object, blocking=True)
            SideBarGit().quickPanel(
                self.on_done, repo.repository, (SideBarGit.last_stdout).split("\n")
            )

    def on_done(self, extra, data, result):
        result = data[result].strip()
        if result.startswith("*"):
            return
        else:
            branch = result.split(" ")[0]
            object = Object()
            object.item = extra
            object.command = ["git", "branch", "-D", branch]
            object.to_status_bar = True
            SideBarGit().run(object)

    def is_enabled(self, paths=[]):
        return SideBarSelection(paths).len() > 0


class sidebar_git_status_bar_branch(sublime_plugin.EventListener):
    def on_load(self, v):
        if v.file_name() and not v.settings().get("is_widget"):
            sidebar_git_status_bar_branch_get(v.file_name(), v).start()
        else:
            v.set_status("statusbar_sidebargit_branch", "")

    def on_activated(self, v):
        if v.file_name() and not v.settings().get("is_widget"):
            sidebar_git_status_bar_branch_get(v.file_name(), v).start()
        else:
            v.set_status("statusbar_sidebargit_branch", "")


class sidebar_git_status_bar_branch_get(threading.Thread):
    def __init__(self, file_name, v):
        threading.Thread.__init__(self)
        self.file_name = file_name
        self.v = v

    def run(self):
        for repo in SideBarGit().getSelectedRepos(
            SideBarSelection([self.file_name]).getSelectedItems()
        ):
            object = Object()
            object.item = repo.repository
            object.command = ["git", "branch"]
            object.silent = True
            SideBarGit().run(object)
            sublime.set_timeout(lambda: self.on_done(SideBarGit.last_stdout), 0)
            return

    def on_done(self, branches):
        branches = branches.split("\n")
        for branch in branches:
            if branch.startswith("*"):
                self.v.set_status("statusbar_sidebargit_branch", branch)
                return


# todo
# class SideBarGitRebaseCurrentIntoMasterCommand(sublime_plugin.WindowCommand):
#     def run(self, paths=[]):
#         for repo in SideBarGit().getSelectedRepos(
#             SideBarSelection(paths).getSelectedItems()
#         ):
#             object = Object()
#             object.item = repo.repository
#             object.command = ["git", "rebase", "master"]
#             SideBarGit().run(object)

#     def is_enabled(self, paths=[]):
#         return SideBarSelection(paths).len() > 0
