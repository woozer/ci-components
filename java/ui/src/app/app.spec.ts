import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { App } from './app';

const animals = [{ id: 7, name: 'Keizerspinguïn', habitat: 'Antarctica', diet: 'Vleeseter' }];

describe('Animal discovery', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads animals from the API and renders their fields in a table', async () => {
    const fixture = TestBed.createComponent(App);
    http.expectOne('/api/animals').flush(animals);
    await fixture.whenStable();
    const row = fixture.nativeElement.querySelector('tbody tr');
    expect(row.textContent).toContain('Keizerspinguïn');
    expect(row.textContent).toContain('Antarctica');
    expect(row.textContent).toContain('Vleeseter');
  });

  it('refreshes the selection and prevents simultaneous requests', async () => {
    const fixture = TestBed.createComponent(App);
    http.expectOne('/api/animals').flush(animals);
    await fixture.whenStable();
    fixture.nativeElement.querySelector('button').click();
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('button').disabled).toBe(true);
    fixture.componentInstance.refresh();
    const request = http.expectOne('/api/animals');
    request.flush([{ id: 5, name: 'Capibara', habitat: 'Moeras', diet: 'Planteneter' }]);
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('tbody').textContent).toContain('Capibara');
    expect(fixture.nativeElement.querySelector('tbody').textContent).not.toContain(
      'Keizerspinguïn',
    );
    expect(fixture.nativeElement.querySelector('button').disabled).toBe(false);
  });

  it('shows a recoverable error and retains an existing selection', async () => {
    const fixture = TestBed.createComponent(App);
    http.expectOne('/api/animals').flush(animals);
    fixture.componentInstance.refresh();
    http.expectOne('/api/animals').flush('Unavailable', { status: 503, statusText: 'Unavailable' });
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain(
      'Probeer het opnieuw',
    );
    expect(fixture.nativeElement.querySelector('tbody').textContent).toContain('Keizerspinguïn');
    expect(fixture.nativeElement.querySelector('button').disabled).toBe(false);
  });

  it('shows an empty state when the API returns no animals', async () => {
    const fixture = TestBed.createComponent(App);
    http.expectOne('/api/animals').flush([]);
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Nog geen dieren gevonden');
    expect(fixture.nativeElement.querySelector('table')).toBeNull();
  });
});
