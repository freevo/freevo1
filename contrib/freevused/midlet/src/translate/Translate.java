package translate;

public class Translate extends Translation {

	private static Translate ref;
	private static Translation translation;
		
	private Translate() {
	}

	public static final Translate getInstance() {
		if (ref == null)
			ref = new Translate();

		return ref;

	}

	public static final String get(Object msg) {
		Object r;

		if ( items.containsKey(msg) ) {
			r = items.get(msg);
		} else {
			r = msg;
		}

		return r.toString();
	}

}
