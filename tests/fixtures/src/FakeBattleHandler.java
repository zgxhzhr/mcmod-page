package fake;

/** 闸门回归用的假源码：只有这里出现的数字/词才算「有出处」。 */
public class FakeBattleHandler {
    static final double ARENA_HALF = 48.0;
    private static final int WAVE_SIZE = 20;
    private static final int WAVE_SECONDS = 60;
    private static final int WAVE_INTERVAL_TICKS = 1200;
    private static final double WIN_RATIO = 0.8;
    private static final String TITLE = "你遭遇了亡灵大军";
    private static final String UNDEAD_TROOPS = "麾下 %s 名亡灵";
}
