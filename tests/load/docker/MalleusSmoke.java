import org.jitsi.meet.test.MalleusJitsificus;

/** Runs the actual Malleus orchestration with zero peers and no network. */
public final class MalleusSmoke {
    @org.testng.annotations.Test
    public void executesRealMalleusWithoutMeeting() throws Exception {
        main(new String[0]);
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 1 && args[0].equals("--prepare-driver")) {
            io.github.bonigarcia.wdm.WebDriverManager.chromedriver()
                .driverVersion("130.0.6723.91").cachePath("/opt/malleus/driver-cache").setup();
            System.out.println("PINNED_DRIVER_CACHE_READY");
            return;
        }
        new MalleusJitsificus().testMain(null, 0, 0L, 0L, 0, 0,
            null, 0.0f, false, 1, 1, 1, 1, null, null, false);
        System.out.println("MALLEUS_EXECUTION_OK_ZERO_PEERS_NO_MEETING");
    }
}
