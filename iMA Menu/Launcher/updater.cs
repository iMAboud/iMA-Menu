using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Threading;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Security.Principal;

[ComImport]
[Guid("00021401-0000-0000-C000-000000000046")]
internal class ShellLink {}

[ComImport]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
[Guid("000214F9-0000-0000-C000-000000000046")]
internal interface IShellLinkW {
    void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszFile, int cchMaxPath, IntPtr pfd, int fFlags);
    void GetIDList(out IntPtr ppidl);
    void SetIDList(IntPtr pidl);
    void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszName, int cchMaxName);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string pszName);
    void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszDir, int cchMaxPath);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string pszDir);
    void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszArgs, int cchMaxPath);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string pszArgs);
    void GetHotkey(out short pwHotkey);
    void SetHotkey(short wHotkey);
    void GetShowCmd(out int piShowCmd);
    void SetShowCmd(int iShowCmd);
    void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder pszIconPath, int cchIconPath, out int piIcon);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string pszIconPath, int iIcon);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string pszPathRel, int dwReserved);
    void Resolve(IntPtr hwnd, int fFlags);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string pszFile);
}

public class Program {
    [DllImport("shell32.dll")]
    private static extern void SHChangeNotify(int wEventId, int uFlags, IntPtr dwItem1, IntPtr dwItem2);

    private static bool SaveShortcut(string lnkPath, string targetExe, string workDir) {
        try {
            string dir = Path.GetDirectoryName(lnkPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
            IShellLinkW link = (IShellLinkW)new ShellLink();
            link.SetPath(targetExe);
            link.SetWorkingDirectory(workDir);
            link.SetArguments("");
            link.SetDescription("iMA Menu");
            link.SetShowCmd(1);
            link.SetIconLocation(targetExe, 0);
            IPersistFile file = (IPersistFile)link;
            file.Save(lnkPath, true);
            return File.Exists(lnkPath);
        } catch {
            return false;
        }
    }

    private static void EnsureStartMenuShortcut(string targetExe, string appDir) {
        try {
            if (string.IsNullOrEmpty(targetExe) && !string.IsNullOrEmpty(appDir)) {
                targetExe = Path.Combine(appDir, "launcher.exe");
            }
            if (string.IsNullOrEmpty(targetExe) || !File.Exists(targetExe)) return;
            targetExe = Path.GetFullPath(targetExe);
            string workDir = Path.GetDirectoryName(targetExe);

            string commonPrograms = Environment.GetFolderPath(Environment.SpecialFolder.CommonPrograms);
            string userPrograms = Environment.GetFolderPath(Environment.SpecialFolder.Programs);
            bool commonSaved = false;

            if (!string.IsNullOrEmpty(commonPrograms) && Directory.Exists(commonPrograms)) {
                string commonDir = Path.Combine(commonPrograms, "iMA Menu");
                string commonLnk = Path.Combine(commonDir, "iMA Menu.lnk");
                string commonRootLnk = Path.Combine(commonPrograms, "iMA Menu.lnk");
                if (File.Exists(commonRootLnk)) {
                    try { File.Delete(commonRootLnk); } catch {}
                }
                if (File.Exists(commonLnk) || Directory.Exists(commonDir)) {
                    commonSaved = SaveShortcut(commonLnk, targetExe, workDir);
                    if (!commonSaved && File.Exists(commonLnk)) {
                        try { File.Delete(commonLnk); } catch {}
                    }
                }
            }

            if (!string.IsNullOrEmpty(userPrograms)) {
                string userDir = Path.Combine(userPrograms, "iMA Menu");
                string userLnk = Path.Combine(userDir, "iMA Menu.lnk");
                string userRootLnk = Path.Combine(userPrograms, "iMA Menu.lnk");
                if (File.Exists(userRootLnk)) {
                    try { File.Delete(userRootLnk); } catch {}
                }
                if (commonSaved) {
                    if (File.Exists(userLnk)) {
                        try { File.Delete(userLnk); } catch {}
                    }
                } else {
                    SaveShortcut(userLnk, targetExe, workDir);
                }
            }
            SHChangeNotify(0x08000000, 0, IntPtr.Zero, IntPtr.Zero);
        } catch {}
    }

    private static void EnsureFolderPermissions(string appDir) {
        try {
            if (string.IsNullOrEmpty(appDir) || !Directory.Exists(appDir)) return;
            string parentDir = Path.GetFullPath(Path.Combine(appDir, ".."));
            string targetDir = Directory.Exists(parentDir) ? parentDir : appDir;

            ProcessStartInfo psi = new ProcessStartInfo {
                FileName = "icacls.exe",
                Arguments = "\"" + targetDir + "\" /grant *S-1-5-32-545:(OI)(CI)M /t /c /q",
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process p = Process.Start(psi);
            if (p != null) p.WaitForExit(8000);
        } catch {}
    }
    [DllImport("userenv.dll", SetLastError = true)]
    private static extern bool CreateEnvironmentBlock(out IntPtr lpEnvironment, IntPtr hToken, bool bInherit);

    [DllImport("userenv.dll", SetLastError = true)]
    private static extern bool DestroyEnvironmentBlock(IntPtr lpEnvironment);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(IntPtr ProcessHandle, uint DesiredAccess, out IntPtr TokenHandle);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr hObject);

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool CreateProcess(
        string lpApplicationName,
        string lpCommandLine,
        IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes,
        bool bInheritHandles,
        uint dwCreationFlags,
        IntPtr lpEnvironment,
        string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo,
        out PROCESS_INFORMATION lpProcessInformation
    );

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct STARTUPINFO {
        public int cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public int dwX;
        public int dwY;
        public int dwXSize;
        public int dwYSize;
        public int dwXCountChars;
        public int dwYCountChars;
        public int dwFillAttribute;
        public int dwFlags;
        public short wShowWindow;
        public short cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct PROCESS_INFORMATION {
        public IntPtr hProcess;
        public IntPtr hThread;
        public int dwProcessId;
        public int dwThreadId;
    }

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool MoveFileEx(string lpExistingFileName, string lpNewFileName, int dwFlags);

    private const int MOVEFILE_DELAY_UNTIL_REBOOT = 0x4;

    private static bool IsAdministrator() {
        try {
            var id = WindowsIdentity.GetCurrent();
            return id != null && new WindowsPrincipal(id).IsInRole(WindowsBuiltInRole.Administrator);
        } catch {
            return false;
        }
    }

    private static void ScheduleOrDelete(string path) {
        if (string.IsNullOrEmpty(path) || !File.Exists(path)) return;
        try {
            File.Delete(path);
        } catch {
            try { MoveFileEx(path, null, MOVEFILE_DELAY_UNTIL_REBOOT); } catch {}
        }
    }

    private static void CleanupOldPrefix(string targetPath) {
        try {
            string dir = Path.GetDirectoryName(targetPath);
            string name = Path.GetFileName(targetPath);
            if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return;
            foreach (string candidate in Directory.GetFiles(dir, name + ".old*")) {
                try { File.Delete(candidate); } catch {}
            }
        } catch {}
    }

    private static bool SwapBinaryWithBackup(string srcPath, string destPath, int maxAttempts = 20) {
        if (string.IsNullOrEmpty(srcPath) || !File.Exists(srcPath) || string.IsNullOrEmpty(destPath))
            return false;
        CleanupOldPrefix(destPath);
        string uniqueOld = destPath + ".old." + DateTime.UtcNow.Ticks;
        for (int i = 0; i < maxAttempts; i++) {
            try {
                if (File.Exists(uniqueOld)) {
                    uniqueOld = destPath + ".old." + DateTime.UtcNow.Ticks + "." + i;
                }
                if (File.Exists(destPath)) {
                    File.Move(destPath, uniqueOld);
                }
                File.Copy(srcPath, destPath, true);
                ScheduleOrDelete(uniqueOld);
                return true;
            } catch {
                Thread.Sleep(500);
            }
        }
        return false;
    }

    private static Version GetDllVersion(string path) {
        try {
            if (File.Exists(path)) {
                var info = FileVersionInfo.GetVersionInfo(path);
                return new Version(info.FileMajorPart, info.FileMinorPart, info.FileBuildPart, info.FilePrivatePart);
            }
        } catch {}
        return new Version(0, 0, 0, 0);
    }

    public static int Main(string[] args) {
        try {
            int parentPid = 0;
            string targetExe = "";
            string newExe = "";
            string oldExe = "";
            string appDir = "";
            string newShellDll = "";
            string newShellExe = "";
            string targetShellDll = "";
            string shellExe = "";
            bool shellOnly = false;

            for (int i = 0; i < args.Length; i++) {
                if (args[i] == "--pid" && i + 1 < args.Length) parentPid = int.Parse(args[++i]);
                else if (args[i] == "--target" && i + 1 < args.Length) targetExe = args[++i];
                else if (args[i] == "--new" && i + 1 < args.Length) newExe = args[++i];
                else if (args[i] == "--old" && i + 1 < args.Length) oldExe = args[++i];
                else if (args[i] == "--dir" && i + 1 < args.Length) appDir = args[++i];
                else if (args[i] == "--new-shell" && i + 1 < args.Length) newShellDll = args[++i];
                else if (args[i] == "--new-shell-exe" && i + 1 < args.Length) newShellExe = args[++i];
                else if (args[i] == "--target-shell" && i + 1 < args.Length) targetShellDll = args[++i];
                else if (args[i] == "--shell-exe" && i + 1 < args.Length) shellExe = args[++i];
                else if (args[i] == "--shell-only") shellOnly = true;
            }

            if (parentPid > 0) {
                try {
                    Process parent = Process.GetProcessById(parentPid);
                    parent.WaitForExit(15000);
                } catch {}
            }

            Thread.Sleep(1000);

            if (string.IsNullOrEmpty(targetShellDll) && !string.IsNullOrEmpty(appDir)) {
                string parentDir = Path.GetFullPath(Path.Combine(appDir, ".."));
                targetShellDll = Path.Combine(parentDir, "shell.dll");
            }
            if (string.IsNullOrEmpty(shellExe) && !string.IsNullOrEmpty(targetShellDll)) {
                string parentDir = Path.GetDirectoryName(targetShellDll);
                shellExe = Path.Combine(parentDir, "shell.exe");
            }

            Version currentDllVer = GetDllVersion(targetShellDll);
            Version bundledDllVer = GetDllVersion(newShellDll);
            Version currentExeVer = GetDllVersion(shellExe);
            Version bundledExeVer = GetDllVersion(newShellExe);

            bool needDllSwap = !string.IsNullOrEmpty(newShellDll) && File.Exists(newShellDll) &&
                (!File.Exists(targetShellDll) || currentDllVer < bundledDllVer || (shellOnly && currentDllVer != bundledDllVer));
            bool needExeSwap = !string.IsNullOrEmpty(newShellExe) && File.Exists(newShellExe) &&
                (!File.Exists(shellExe) || currentExeVer < bundledExeVer || (shellOnly && currentExeVer != bundledExeVer));

            bool canRegisterShell = shellOnly || IsAdministrator();

            if (canRegisterShell && (needDllSwap || needExeSwap)) {
                // 1. Unregister and restart explorer to release COM/shell handles
                if (!string.IsNullOrEmpty(shellExe) && File.Exists(shellExe)) {
                    try {
                        ProcessStartInfo unregPsi = new ProcessStartInfo {
                            FileName = shellExe,
                            Arguments = "-u -s -restart",
                            UseShellExecute = false,
                            CreateNoWindow = true
                        };
                        Process unregProc = Process.Start(unregPsi);
                        if (unregProc != null) unregProc.WaitForExit(10000);
                    } catch {}
                }

                // 2. Wait for explorer restart to unload shell.dll cleanly
                Thread.Sleep(2000);

                // 3. Atomically swap shell.dll and shell.exe using unique backup names
                bool shellCopied = !needDllSwap || SwapBinaryWithBackup(newShellDll, targetShellDll, 20);
                bool exeCopied = !needExeSwap || SwapBinaryWithBackup(newShellExe, shellExe, 20);

                // 4. Register updated shell.dll and restart explorer
                if (!string.IsNullOrEmpty(shellExe) && File.Exists(shellExe)) {
                    try {
                        ProcessStartInfo regPsi = new ProcessStartInfo {
                            FileName = shellExe,
                            Arguments = "-r -s -restart",
                            UseShellExecute = false,
                            CreateNoWindow = true
                        };
                        Process regProc = Process.Start(regPsi);
                        if (regProc != null) regProc.WaitForExit(10000);
                    } catch {}
                }

                Thread.Sleep(1500);
                try {
                    if (Process.GetProcessesByName("explorer").Length == 0) {
                        Process.Start(new ProcessStartInfo {
                            FileName = "explorer.exe",
                            UseShellExecute = true
                        });
                    }
                } catch {}

                if (File.Exists(newShellDll)) {
                    try { File.Delete(newShellDll); } catch {}
                }
                if (File.Exists(newShellExe)) {
                    try { File.Delete(newShellExe); } catch {}
                }

                if (shellOnly) {
                    return (shellCopied && exeCopied) ? 0 : 4;
                }
            } else {
                if (!string.IsNullOrEmpty(newShellDll) && File.Exists(newShellDll)) {
                    try { File.Delete(newShellDll); } catch {}
                }
                if (!string.IsNullOrEmpty(newShellExe) && File.Exists(newShellExe)) {
                    try { File.Delete(newShellExe); } catch {}
                }
                if (shellOnly) {
                    return 0;
                }
            }

            if (string.IsNullOrEmpty(newExe) || string.IsNullOrEmpty(targetExe)) {
                return 0;
            }

            bool swapped = false;
            for (int i = 0; i < 15; i++) {
                try {
                    if (File.Exists(oldExe)) File.Delete(oldExe);
                    if (File.Exists(targetExe)) File.Move(targetExe, oldExe);
                    File.Copy(newExe, targetExe, true);
                    if (File.Exists(newExe)) File.Delete(newExe);
                    swapped = true;
                    break;
                } catch {
                    Thread.Sleep(500);
                }
            }

            if (File.Exists(oldExe)) {
                try { File.Delete(oldExe); } catch {}
            }

            if (!swapped) return 1;

            EnsureStartMenuShortcut(targetExe, appDir);
            EnsureFolderPermissions(appDir);

            IntPtr token = IntPtr.Zero;
            IntPtr envBlock = IntPtr.Zero;
            bool created = false;

            if (OpenProcessToken(Process.GetCurrentProcess().Handle, 0x0028, out token)) {
                CreateEnvironmentBlock(out envBlock, token, false);
            }

            STARTUPINFO si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(si);
            PROCESS_INFORMATION pi = new PROCESS_INFORMATION();

            uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
            uint DETACHED_PROCESS = 0x00000008;

            created = CreateProcess(
                targetExe,
                "\"" + targetExe + "\"",
                IntPtr.Zero,
                IntPtr.Zero,
                false,
                CREATE_UNICODE_ENVIRONMENT | DETACHED_PROCESS,
                envBlock != IntPtr.Zero ? envBlock : IntPtr.Zero,
                appDir,
                ref si,
                out pi
            );

            if (envBlock != IntPtr.Zero) DestroyEnvironmentBlock(envBlock);
            if (token != IntPtr.Zero) CloseHandle(token);
            if (pi.hProcess != IntPtr.Zero) CloseHandle(pi.hProcess);
            if (pi.hThread != IntPtr.Zero) CloseHandle(pi.hThread);

            return created ? 0 : 2;
        } catch {
            return 3;
        }
    }
}
