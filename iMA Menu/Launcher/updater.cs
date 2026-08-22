using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Runtime.InteropServices;

public class Program {
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

            Thread.Sleep(500);

            if (string.IsNullOrEmpty(targetShellDll)) {
                string parentDir = Path.GetFullPath(Path.Combine(appDir, ".."));
                targetShellDll = Path.Combine(parentDir, "shell.dll");
            }
            if (string.IsNullOrEmpty(shellExe)) {
                string parentDir = Path.GetDirectoryName(targetShellDll);
                shellExe = Path.Combine(parentDir, "shell.exe");
            }

            Version minVersion = new Version(2, 0, 0, 2);
            Version currentVersion = GetDllVersion(targetShellDll);

            if (File.Exists(newShellDll) && (shellOnly || currentVersion < minVersion)) {
                // 1. Unregister and restart explorer
                if (File.Exists(shellExe)) {
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

                // 2. Extra safety wait for explorer restart to release file handles
                Thread.Sleep(2000);

                // 3. Move/replace shell.dll with new v2.0.0.2
                string oldShellDll = targetShellDll + ".old";
                bool shellCopied = false;
                for (int i = 0; i < 20; i++) {
                    try {
                        if (File.Exists(oldShellDll)) File.Delete(oldShellDll);
                        if (File.Exists(targetShellDll)) File.Move(targetShellDll, oldShellDll);
                        File.Copy(newShellDll, targetShellDll, true);
                        shellCopied = true;
                        break;
                    } catch {
                        Thread.Sleep(500);
                    }
                }
                if (File.Exists(oldShellDll)) {
                    try { File.Delete(oldShellDll); } catch {}
                }

                // Copy new shell.exe if provided
                if (File.Exists(newShellExe)) {
                    string oldShellExe = shellExe + ".old";
                    for (int i = 0; i < 20; i++) {
                        try {
                            if (File.Exists(oldShellExe)) File.Delete(oldShellExe);
                            if (File.Exists(shellExe)) File.Move(shellExe, oldShellExe);
                            File.Copy(newShellExe, shellExe, true);
                            break;
                        } catch {
                            Thread.Sleep(500);
                        }
                    }
                    if (File.Exists(oldShellExe)) {
                        try { File.Delete(oldShellExe); } catch {}
                    }
                }

                // 4. Register new shell.dll and restart explorer
                if (File.Exists(shellExe)) {
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

                if (File.Exists(newShellDll)) {
                    try { File.Delete(newShellDll); } catch {}
                }
                if (File.Exists(newShellExe)) {
                    try { File.Delete(newShellExe); } catch {}
                }

                if (shellOnly) {
                    return shellCopied ? 0 : 4;
                }
            } else {
                if (File.Exists(newShellDll)) {
                    try { File.Delete(newShellDll); } catch {}
                }
                if (File.Exists(newShellExe)) {
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
